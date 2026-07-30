"""scenes/teacher_dashboard.py — PIN gate, per-student overview, reset-progress."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button
from typecraft.ui.scroll_panel import ScrollPanel
from typecraft.ui.text_input import TextInput

ROW_HEIGHT = 44
FIRST_ROW_Y = 180

#: Column layout: (heading, x, key, formatter). One place to change the table.
COLUMNS = [
    ("Student", 60, "name", lambda v: str(v)),
    ("Lvl", 300, "level", lambda v: str(v)),
    ("XP", 350, "total_xp", lambda v: str(v)),
    ("Avg WPM", 420, "avg_wpm_net", lambda v: "—" if v is None else f"{v:.0f}"),
    ("Avg Acc", 520, "avg_accuracy", lambda v: "—" if v is None else f"{v:.0f}%"),
    ("Lessons", 620, "lessons_completed", lambda v: str(v)),
    ("Badges", 720, "badge_count", lambda v: str(v)),
    ("Streak", 810, "current_streak", lambda v: f"{v}d"),
    ("Best", 880, "longest_streak", lambda v: f"{v}d"),
]


class TeacherDashboardScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.authenticated = not self.ctx.config.has_pin()  # no PIN set yet -> open, teacher should set one
        self.error = ""
        #: The student awaiting reset confirmation, or None. Reset is destructive and
        #: irreversible, so it never happens on a single click (FR-125).
        self.pending_reset = None
        self.panel = ScrollPanel(pygame.Rect(0, FIRST_ROW_Y, theme.SCREEN_WIDTH, 500))
        self._build_pin_widgets()
        self._build_dashboard_widgets()

    def _build_pin_widgets(self) -> None:
        cx = theme.SCREEN_WIDTH // 2
        self.pin_input = TextInput(pygame.Rect(cx - 100, 300, 200, 44), self.ctx.resources,
                                    placeholder="Enter PIN", max_length=4, is_password=True,
                                    on_submit=self._try_pin)
        self.submit_button = Button(pygame.Rect(cx - 90, 360, 180, 46), "Unlock",
                                     self._try_pin, self.ctx.resources)
        self.back_button = Button(pygame.Rect(20, 20, 100, 44), "Back",
                                   lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
                                   bg_color=theme.COLOR_TEXT_MUTED)

    def _build_dashboard_widgets(self) -> None:
        """One row per student inside a scrolling viewport (FR-124).

        A fixed list ran off the bottom of the window at about twelve students, so
        the rest of a real class - and their Reset buttons - were simply not there.
        Rows are laid out in the panel's content space, starting at y = 0.
        """
        self.reset_buttons = []
        self.summaries = self.ctx.progression.class_summary()

        y = 0
        for summary in self.summaries:
            rect = pygame.Rect(theme.SCREEN_WIDTH - 180, y - 4, 120, 32)
            self.reset_buttons.append((summary, Button(
                rect, "Reset", lambda s=summary: self._ask_reset(s),
                self.ctx.resources, bg_color=theme.COLOR_ERROR,
                font_size=theme.FONT_SIZE_SMALL)))
            y += ROW_HEIGHT
        self.panel.set_content_height(y)

        cx = theme.SCREEN_WIDTH // 2
        self.confirm_button = Button(pygame.Rect(cx - 200, 420, 180, 46), "Yes, reset",
                                      self._confirm_reset, self.ctx.resources,
                                      bg_color=theme.COLOR_ERROR)
        self.cancel_button = Button(pygame.Rect(cx + 20, 420, 180, 46), "Cancel",
                                     self._cancel_reset, self.ctx.resources,
                                     bg_color=theme.COLOR_TEXT_MUTED)

    def _try_pin(self) -> None:
        if self.ctx.config.verify_pin(self.pin_input.text):
            self.authenticated = True
            self.error = ""
        else:
            self.error = "Incorrect PIN"
        self.pin_input.text = ""

    # --- reset ------------------------------------------------------------

    def _ask_reset(self, summary) -> None:
        """First click only arms the confirmation; nothing is written yet."""
        self.pending_reset = summary

    def _cancel_reset(self) -> None:
        self.pending_reset = None

    def _confirm_reset(self) -> None:
        summary = self.pending_reset
        if summary is None:
            return
        self._reset_progress(self.ctx.profiles.load(summary["profile_id"]))
        self.pending_reset = None
        self._build_dashboard_widgets()   # refresh the now-zeroed figures

    def _reset_progress(self, profile) -> None:
        """Wipe this student's attempts/progress/badges and zero their XP, level
        and streaks, keeping the profile row (id/name/avatar) so the child does not
        have to be re-created, and re-unlocking lesson 1 (FR-126, FR-127).

        One transaction, all of it. A reset that half-applied would leave a child
        with no history and a level they can no longer have earned.
        """
        with self.ctx.db.transaction():
            self.ctx.db.execute("DELETE FROM lesson_attempts WHERE profile_id=?", (profile.id,))
            self.ctx.db.execute("DELETE FROM lesson_progress WHERE profile_id=?", (profile.id,))
            self.ctx.db.execute("DELETE FROM profile_badges WHERE profile_id=?", (profile.id,))
            self.ctx.db.execute(
                """UPDATE profiles SET total_xp=0, level=1, current_streak=0,
                   longest_streak=0, last_active_date=NULL WHERE id=?""",
                (profile.id,),
            )
            first = self.ctx.lessons.first_lesson()
            if first:
                self.ctx.db.execute(
                    "INSERT INTO lesson_progress (profile_id, lesson_id, is_unlocked) VALUES (?,?,1)",
                    (profile.id, first.id),
                )

        # Keep the in-memory Profile consistent with the row we just wrote, or a
        # later save() would resurrect the XP this reset just cleared.
        profile.total_xp = 0
        profile.level = 1
        profile.current_streak = 0
        profile.longest_streak = 0
        profile.last_active_date = None

        if self.ctx.active_profile is not None and self.ctx.active_profile.id == profile.id:
            self.ctx.active_profile = profile

    # --- event / update / render ------------------------------------------

    def handle_event(self, event) -> None:
        if self.pending_reset is not None:
            # The confirmation is modal: nothing behind it can be clicked, so a
            # stray click cannot reset the wrong child.
            if self.confirm_button.handle_event(event):
                return
            if self.cancel_button.handle_event(event):
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._cancel_reset()
            return

        if self.back_button.handle_event(event):
            return
        if not self.authenticated:
            if self.pin_input.handle_event(event):
                return
            if self.submit_button.handle_event(event):
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._try_pin()
            return

        if self.panel.handle_event(event):
            return
        local = self.panel.translated(event) if hasattr(event, "pos") else event
        if local is None:
            return
        for _, btn in self.reset_buttons:
            if btn.handle_event(local):
                return

    def update(self, dt: float) -> None:
        if not self.authenticated:
            self.pin_input.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)

        if not self.authenticated:
            self.back_button.render(surface)
            title = self.ctx.resources.text_surface("Teacher PIN", font_h, theme.COLOR_TEXT)
            surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 220)))
            self.pin_input.render(surface)
            self.submit_button.render(surface)
            if self.error:
                font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
                err_surf = self.ctx.resources.text_surface(self.error, font_small, theme.COLOR_ERROR)
                surface.blit(err_surf, err_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 420)))
            return

        self.back_button.render(surface)
        title = self.ctx.resources.text_surface("Class Overview", font_h, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 70)))

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        sub = self.ctx.resources.text_surface(
            "Tap a student row to reset their progress", font_small, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, 105)))

        self._render_table(surface)

        if self.pending_reset is not None:
            self._render_confirmation(surface)

    def _render_table(self, surface) -> None:
        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)

        for heading, x, _key, _fmt in COLUMNS:
            surf = self.ctx.resources.text_surface(heading, font_small, theme.COLOR_TEXT_MUTED)
            surface.blit(surf, (x, FIRST_ROW_Y - 30))

        if not self.summaries:
            empty = self.ctx.resources.text_surface(
                "No students yet.", font_small, theme.COLOR_TEXT_MUTED)
            surface.blit(empty, (60, FIRST_ROW_Y))
            return

        with self.panel.clipped(surface):
            y = 0
            for summary, btn in self.reset_buttons:
                row = pygame.Rect(0, y, theme.SCREEN_WIDTH, ROW_HEIGHT)
                if self.panel.is_visible(row):
                    screen_y = self.panel.screen_rect(row).y
                    for _heading, x, key, fmt in COLUMNS:
                        surf = self.ctx.resources.text_surface(
                            fmt(summary[key]), font_small, theme.COLOR_TEXT)
                        surface.blit(surf, (x, screen_y))
                    original = btn.rect
                    btn.rect = self.panel.screen_rect(original)
                    try:
                        btn.render(surface)
                    finally:
                        btn.rect = original
                y += ROW_HEIGHT
        self.panel.render_scrollbar(surface, theme.COLOR_PRIMARY, theme.COLOR_LOCKED)

        # Averages cover completed attempts only, so say so — a dash means "nothing
        # finished yet", which is different from zero (FR-123).
        note = self.ctx.resources.text_surface(
            "Averages use completed lessons only. — means nothing finished yet.",
            font_small, theme.COLOR_TEXT_MUTED)
        surface.blit(note, (60, theme.SCREEN_HEIGHT - 36))

    def _render_confirmation(self, surface) -> None:
        summary = self.pending_reset
        panel = pygame.Rect(theme.SCREEN_WIDTH // 2 - 320, 280, 640, 210)

        shade = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surface.blit(shade, (0, 0))

        pygame.draw.rect(surface, theme.COLOR_CARD_BG, panel, border_radius=14)
        pygame.draw.rect(surface, theme.COLOR_ERROR, panel, width=3, border_radius=14)

        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)

        heading = self.ctx.resources.text_surface(
            f"Reset {summary['name']}?", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(panel.centerx, panel.y + 45)))

        for i, line in enumerate((
            f"This erases {summary['completed_attempts']} completed lessons, "
            f"{summary['total_xp']} XP and {summary['badge_count']} badges.",
            "Their name and avatar are kept. This cannot be undone.",
        )):
            surf = self.ctx.resources.text_surface(line, font_small, theme.COLOR_TEXT_MUTED)
            surface.blit(surf, surf.get_rect(center=(panel.centerx, panel.y + 90 + i * 24)))

        self.confirm_button.render(surface)
        self.cancel_button.render(surface)
