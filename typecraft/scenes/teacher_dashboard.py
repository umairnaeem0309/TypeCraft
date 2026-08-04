"""scenes/teacher_dashboard.py — PIN gate, class overview, sync, and reset-progress."""

import pygame

from typecraft.core.paths import writable_data_dir
from typecraft.managers.sync_manager import SyncError

from typecraft.core.scene import Scene
from typecraft.ui import screen, theme
from typecraft.ui.button import Button
from typecraft.ui.scroll_panel import ScrollPanel
from typecraft.ui.text_input import TextInput

ROW_HEIGHT = 52

#: The dashboard header has three deliberate bands: page title/subtitle, the
#: teacher toolbar, then the table headings. Keeping the toolbar out of the table
#: band prevents the action buttons from covering headings at the design size.
TOOLBAR_Y = 146
TOOLBAR_HEIGHT = 48
FIRST_ROW_Y = 252

#: Column headings sit above the scrolling rows, with a rule separating the two.
HEADER_Y = FIRST_ROW_Y - 40
HEADER_RULE_Y = FIRST_ROW_Y - 10

#: Authenticated teacher-only controls. These are grouped in one toolbar row and
#: use calm secondary colours so routine actions do not compete with the table.
EXPORT_RESULTS_RECT = pygame.Rect(520, TOOLBAR_Y, 190, TOOLBAR_HEIGHT)
IMPORT_RESULTS_RECT = pygame.Rect(730, TOOLBAR_Y, 190, TOOLBAR_HEIGHT)
CHANGE_PIN_RECT = pygame.Rect(940, TOOLBAR_Y, 200, TOOLBAR_HEIGHT)

#: PIN-change dialog geometry, kept separate from the table and its reset modal.
PIN_CHANGE_PANEL = pygame.Rect(theme.SCREEN_WIDTH // 2 - 300, 155, 600, 440)



#: Column layout: (heading, key, formatter). Positions are **measured**, not written
#: down — see `_measure_columns()`. Hard-coded x values collided the moment the
#: headings became bold and upper-case, because they got wider than the numbers
#: underneath them.
COLUMNS = [
    ("Student", "name", lambda v: str(v)),
    ("Lvl", "level", lambda v: str(v)),
    ("XP", "total_xp", lambda v: str(v)),
    ("Avg WPM", "avg_wpm_net", lambda v: "—" if v is None else f"{v:.0f}"),
    ("Avg Acc", "avg_accuracy", lambda v: "—" if v is None else f"{v:.0f}%"),
    ("Lessons", "lessons_completed", lambda v: str(v)),
    ("Badges", "badge_count", lambda v: str(v)),
    ("Streak", "current_streak", lambda v: f"{v}d"),
    ("Best", "longest_streak", lambda v: f"{v}d"),
]

#: Table margins and the gap between columns.
TABLE_X = 60
COLUMN_GAP = 22
#: The Student column also has to fit a name like "Mustafa Iqbal".
STUDENT_MIN_WIDTH = 200
#: Right-hand space reserved for the Reset buttons and the scrollbar.
ACTIONS_WIDTH = 220


class TeacherDashboardScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.authenticated = not self.ctx.config.has_pin()  # no PIN set yet -> open, teacher should set one
        self.error = ""
        #: The student awaiting reset confirmation, or None. Reset is destructive and
        #: irreversible, so it never happens on a single click (FR-125).
        self.pending_reset = None
        self.pin_change_open = False
        self.pin_change_error = ""
        self.pin_change_status = ""
        self.sync_status = ""
        self.panel = ScrollPanel(pygame.Rect(0, FIRST_ROW_Y, theme.SCREEN_WIDTH,
                                              theme.SCREEN_HEIGHT - FIRST_ROW_Y - 64))
        # Reusable italic fonts for consistent page subtitles and bottom notes.
        self._subtitle_font = pygame.font.Font(None, theme.FONT_SIZE_HEADING)
        self._subtitle_font.set_italic(True)
        self._note_font = pygame.font.Font(None, theme.FONT_SIZE_BODY)
        self._note_font.set_italic(True)
        # Bold body size for the column headings. Held on the scene because
        # ResourceManager caches rendered text by font identity, so the object must
        # be stable across frames.
        self._header_font = pygame.font.Font(None, theme.FONT_SIZE_BODY)
        self._header_font.set_bold(True)
        self._column_x = self._measure_columns()
        self._build_pin_widgets()
        self._build_pin_change_widgets()
        self._build_sync_widgets()
        self._build_dashboard_widgets()

    def _measure_columns(self) -> list:
        """Lay the columns out from the *rendered width* of each heading.

        The headings are bold and upper-case, which makes them wider than the values
        below; with hard-coded x positions "STREAK" and "BEST" overlapped. Measuring
        means the table stays readable if the heading text, the font or the type
        scale ever changes.
        """
        body_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        x = TABLE_X
        positions = []
        for index, (heading, _key, _fmt) in enumerate(COLUMNS):
            positions.append(x)
            width = self._header_font.size(heading.upper())[0]
            if index == 0:
                width = max(width, STUDENT_MIN_WIDTH)
            else:
                # Values are narrower than these headings in practice, but measure
                # a plausible worst case so a 3-digit XP never runs into "AVG WPM".
                width = max(width, body_font.size("9999")[0])
            x += width + COLUMN_GAP
        return positions

    @property
    def table_right(self) -> int:
        """Where the last column ends — must stay clear of the Reset buttons."""
        last_x = self._column_x[-1]
        return last_x + self._header_font.size(COLUMNS[-1][0].upper())[0]

    def _build_pin_widgets(self) -> None:
        cx = theme.SCREEN_WIDTH // 2
        self.pin_input = TextInput(pygame.Rect(cx - 140, 280, 280, 52), self.ctx.resources,
                                    placeholder="Enter PIN", max_length=4, is_password=True,
                                    on_submit=self._try_pin)
        self.submit_button = Button(pygame.Rect(cx - 110, 350, 220, 54), "Unlock",
                                     self._try_pin, self.ctx.resources)
        self.back_button = screen.back_button(self.ctx, "main_menu")

    def _build_pin_change_widgets(self) -> None:
        """Build the teacher-only PIN-change dialog.

        The dialog is not reachable until ``authenticated`` is true. Existing PIN
        verification is intentionally delegated to ConfigManager so the storage,
        salted hash format, and legacy upgrade path remain unchanged.
        """
        cx = theme.SCREEN_WIDTH // 2
        self.change_pin_button = Button(
            CHANGE_PIN_RECT.copy(),
            "Set PIN" if not self.ctx.config.has_pin() else "Change PIN",
            self._open_pin_change,
            self.ctx.resources,
            bg_color=theme.COLOR_SECONDARY_DARK,
            font_size=theme.FONT_SIZE_SMALL,
        )
        self.current_pin_input = TextInput(
            pygame.Rect(cx - 180, PIN_CHANGE_PANEL.y + 82, 360, 52),
            self.ctx.resources,
            placeholder="Current PIN",
            max_length=4,
            is_password=True,
        )
        self.new_pin_input = TextInput(
            pygame.Rect(cx - 180, PIN_CHANGE_PANEL.y + 150, 360, 52),
            self.ctx.resources,
            placeholder="New 4-digit PIN",
            max_length=4,
            is_password=True,
        )
        self.confirm_pin_input = TextInput(
            pygame.Rect(cx - 180, PIN_CHANGE_PANEL.y + 218, 360, 52),
            self.ctx.resources,
            placeholder="Confirm new PIN",
            max_length=4,
            is_password=True,
            on_submit=self._save_pin_change,
        )
        self.save_pin_button = Button(
            pygame.Rect(cx - 190, PIN_CHANGE_PANEL.bottom - 64, 180, 50),
            "Save PIN",
            self._save_pin_change,
            self.ctx.resources,
            bg_color=theme.COLOR_PRIMARY,
        )
        self.cancel_pin_button = Button(
            pygame.Rect(cx + 10, PIN_CHANGE_PANEL.bottom - 64, 180, 50),
            "Cancel",
            self._cancel_pin_change,
            self.ctx.resources,
            bg_color=theme.COLOR_NEUTRAL,
        )

    def _open_pin_change(self) -> None:
        if not self.authenticated:
            return
        self.pin_change_open = True
        self.pin_change_error = ""
        for field in (self.current_pin_input, self.new_pin_input, self.confirm_pin_input):
            field.text = ""
            field.focused = False
        # A first-time setup has no current PIN to verify. Subsequent changes do.
        self.current_pin_input.visible = self.ctx.config.has_pin()
        self.new_pin_input.focused = not self.current_pin_input.visible

    def _cancel_pin_change(self) -> None:
        self.pin_change_open = False
        self.pin_change_error = ""
        for field in (self.current_pin_input, self.new_pin_input, self.confirm_pin_input):
            field.text = ""
            field.focused = False
            field.visible = True

    def _save_pin_change(self) -> None:
        """Verify the old PIN, validate both new entries, then hash and persist."""
        if not self.pin_change_open:
            return

        if self.ctx.config.has_pin() and not self.ctx.config.verify_pin(
                self.current_pin_input.text.strip()):
            self.pin_change_error = "Incorrect current PIN."
            self.current_pin_input.text = ""
            return

        new_pin = self.new_pin_input.text.strip()
        confirmation = self.confirm_pin_input.text.strip()
        if len(new_pin) != 4 or not new_pin.isdigit():
            self.pin_change_error = "New PIN must be 4 digits."
            return
        if new_pin != confirmation:
            self.pin_change_error = "New PINs do not match."
            self.confirm_pin_input.text = ""
            return

        self.ctx.config.set_pin(new_pin)
        self.change_pin_button.label = "Change PIN"
        self.pin_change_open = False
        self.pin_change_error = ""
        self.pin_change_status = "Teacher PIN updated."
        for field in (self.current_pin_input, self.new_pin_input, self.confirm_pin_input):
            field.text = ""
            field.focused = False
            field.visible = True

    def _build_sync_widgets(self) -> None:
        """Build offline JSON export/import controls.

        Export files are written beside the app's writable data. For an existing
        release, the teacher copies the files from each machine into this same
        folder and clicks Import; no file dialog or external dependency is needed.
        """
        self.export_button = Button(
            EXPORT_RESULTS_RECT.copy(), "Export Results", self._export_results,
            self.ctx.resources, bg_color=theme.COLOR_ACCENT,
            font_size=theme.FONT_SIZE_SMALL,
        )
        self.import_button = Button(
            IMPORT_RESULTS_RECT.copy(), "Import Results", self._import_results,
            self.ctx.resources, bg_color=theme.COLOR_SECONDARY,
            font_size=theme.FONT_SIZE_SMALL,
        )

    def _export_results(self) -> None:
        target = writable_data_dir() / f"typecraft_export_{self.ctx.db.database_id()}.json"
        try:
            self.ctx.sync.export_results(target)
        except (OSError, SyncError) as exc:
            self.sync_status = f"Export failed: {exc}"
            return
        self.sync_status = f"Exported results: {target.name}"

    def _import_results(self) -> None:
        """Import every copied TypeCraft export in the writable app folder."""
        files = sorted(writable_data_dir().glob("typecraft_export_*.json"))
        if not files:
            self.sync_status = "No export files found beside the app."
            return

        profiles_created = attempts_imported = attempts_skipped = 0
        failures = []
        for path in files:
            try:
                result = self.ctx.sync.import_results(path)
            except SyncError as exc:
                # The teacher's own export, or one malformed file, should not
                # prevent the other USB files from importing.
                failures.append(f"{path.name}: {exc}")
                continue
            profiles_created += result["profiles_created"]
            attempts_imported += result["attempts_imported"]
            attempts_skipped += result["attempts_skipped"]

        self._build_dashboard_widgets()
        self.sync_status = (
            f"Imported {attempts_imported} attempts, {profiles_created} new profiles "
            f"({attempts_skipped} already imported)."
        )
        if failures:
            self.sync_status += " " + " ".join(failures)

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
            rect = pygame.Rect(theme.SCREEN_WIDTH - 200, y - 4, 150, 44)
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
        if self.pin_change_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._cancel_pin_change()
                return
            for field in (self.current_pin_input, self.new_pin_input, self.confirm_pin_input):
                if field.handle_event(event):
                    return
            if self.save_pin_button.handle_event(event):
                return
            if self.cancel_pin_button.handle_event(event):
                return
            return

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

        if self.export_button.handle_event(event):
            return
        if self.import_button.handle_event(event):
            return
        if self.change_pin_button.handle_event(event):
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
        if self.pin_change_open:
            for field in (self.current_pin_input, self.new_pin_input, self.confirm_pin_input):
                field.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_PAGE_TITLE)

        if not self.authenticated:
            self.back_button.render(surface)
            title = self.ctx.resources.text_surface("Teacher PIN", font_h, theme.COLOR_TEXT)
            surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                         screen.TITLE_Y)))
            self.pin_input.render(surface)
            self.submit_button.render(surface)
            if self.error:
                font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
                err_surf = self.ctx.resources.text_surface(self.error, font_small, theme.COLOR_ERROR)
                surface.blit(err_surf, err_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 420)))
            return

        self.back_button.render(surface)
        self.export_button.render(surface)
        self.import_button.render(surface)
        self.change_pin_button.render(surface)
        title = self.ctx.resources.text_surface("Class Overview", font_h, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                     screen.TITLE_Y)))

        sub = self.ctx.resources.text_surface(
            "Tap a student row to reset their progress", self._subtitle_font, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, screen.SUBTITLE_Y)))

        self._render_table(surface)

        if self.pending_reset is not None:
            self._render_confirmation(surface)
        if self.pin_change_open:
            self._render_pin_change(surface)

    def _render_table(self, surface) -> None:
        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)

        # Column headings: body-sized and bold in the full text colour, with a rule
        # beneath them. At small/muted they read as a caption rather than as the
        # labels for the numbers below, which is what a teacher scans first.
        for (heading, _key, _fmt), x in zip(COLUMNS, self._column_x):
            surf = self.ctx.resources.text_surface(
                heading.upper(), self._header_font, theme.COLOR_TEXT)
            surface.blit(surf, (x, HEADER_Y))
        pygame.draw.line(surface, theme.COLOR_LOCKED,
                         (TABLE_X, HEADER_RULE_Y),
                         (theme.SCREEN_WIDTH - 50, HEADER_RULE_Y), 2)

        if not self.summaries:
            self._render_empty_state(surface)
            return

        with self.panel.clipped(surface):
            y = 0
            for summary, btn in self.reset_buttons:
                row = pygame.Rect(0, y, theme.SCREEN_WIDTH, ROW_HEIGHT)
                if self.panel.is_visible(row):
                    screen_y = self.panel.screen_rect(row).y
                    for (_heading, key, fmt), x in zip(COLUMNS, self._column_x):
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

        # Use one footer message area. A sync/PIN status temporarily replaces the
        # generic averages note, so the two long italic lines can never overlap.
        note_text = self.sync_status or self.pin_change_status
        if not note_text:
            # Averages cover completed attempts only, so say so — a dash means
            # "nothing finished yet", which is different from zero (FR-123).
            note_text = "Averages use completed lessons only. — means nothing finished yet."
        note = self.ctx.resources.text_surface(
            note_text, self._note_font,
            theme.COLOR_PRIMARY_DARK if (self.sync_status or self.pin_change_status)
            else theme.COLOR_TEXT_MUTED)
        surface.blit(note, note.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                 theme.SCREEN_HEIGHT - 30)))

    EMPTY_TITLE = "No students yet"
    EMPTY_HINT = "Add students from the main menu: Play, then Create Profile."

    def empty_state_layout(self) -> tuple:
        """(title_surface, title_rect, hint_surface, hint_rect), centred in the table.

        Returned rather than drawn inline so the placement is assertable: the message
        used to be small muted text at the far left immediately under the column
        headings, where it read as a stray table row rather than as the state of the
        whole screen.
        """
        area = self.panel.rect
        heading_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        body_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)

        title = self.ctx.resources.text_surface(
            self.EMPTY_TITLE, heading_font, theme.COLOR_TEXT_MUTED)
        hint = self.ctx.resources.text_surface(
            self.EMPTY_HINT, body_font, theme.COLOR_TEXT_MUTED)

        return (title, title.get_rect(center=(area.centerx, area.centery - 18)),
                hint, hint.get_rect(center=(area.centerx, area.centery + 24)))

    def _render_empty_state(self, surface) -> None:
        title, title_rect, hint, hint_rect = self.empty_state_layout()
        surface.blit(title, title_rect)
        surface.blit(hint, hint_rect)

    def _render_pin_change(self, surface) -> None:
        """Render the modal PIN-change flow above the authenticated dashboard."""
        shade = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surface.blit(shade, (0, 0))

        panel = PIN_CHANGE_PANEL
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, panel, border_radius=14)
        pygame.draw.rect(surface, theme.COLOR_ADMIN, panel, width=3, border_radius=14)

        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        heading = self.ctx.resources.text_surface("Change Teacher PIN", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(panel.centerx, panel.y + 36)))

        if self.ctx.config.has_pin():
            hint_text = "Verify the current PIN before saving a new one."
            self.current_pin_input.render(surface)
        else:
            hint_text = "No PIN is set yet. Create one for the Teacher Dashboard."
        hint = self.ctx.resources.text_surface(hint_text, font_body, theme.COLOR_TEXT_MUTED)
        surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 66)))

        self.new_pin_input.render(surface)
        self.confirm_pin_input.render(surface)
        self.save_pin_button.render(surface)
        self.cancel_pin_button.render(surface)

        if self.pin_change_error:
            error = self.ctx.resources.text_surface(
                self.pin_change_error, font_body, theme.COLOR_ERROR)
            surface.blit(error, error.get_rect(center=(panel.centerx, panel.bottom - 94)))

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

        # "Reset Amina?" reads as though the child is being removed. The thing being
        # erased is their work, and the profile itself is kept, so say that.
        heading = self.ctx.resources.text_surface(
            f"Reset {summary['name']}'s data?", font_h, theme.COLOR_TEXT)
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
