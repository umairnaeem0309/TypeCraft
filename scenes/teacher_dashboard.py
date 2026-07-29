"""scenes/teacher_dashboard.py — PIN gate, per-student overview, reset-progress."""

import pygame

from TypeCraft.core.scene import Scene
from TypeCraft.ui import theme
from TypeCraft.ui.button import Button
from TypeCraft.ui.text_input import TextInput


class TeacherDashboardScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.authenticated = not self.ctx.config.has_pin()  # no PIN set yet -> open, teacher should set one
        self.error = ""
        self._build_pin_widgets()
        self._build_dashboard_widgets()

    def _build_pin_widgets(self) -> None:
        cx = theme.SCREEN_WIDTH // 2
        self.pin_input = TextInput(pygame.Rect(cx - 100, 300, 200, 44), self.ctx.resources,
                                    placeholder="Enter PIN", max_length=4, is_password=True)
        self.submit_button = Button(pygame.Rect(cx - 90, 360, 180, 46), "Unlock",
                                     self._try_pin, self.ctx.resources)
        self.back_button = Button(pygame.Rect(20, 20, 100, 44), "Back",
                                   lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
                                   bg_color=theme.COLOR_TEXT_MUTED)

    def _build_dashboard_widgets(self) -> None:
        self.reset_buttons = []
        self.profiles = self.ctx.profiles.list_all()
        y = 160
        for profile in self.profiles:
            rect = pygame.Rect(theme.SCREEN_WIDTH - 220, y, 160, 36)
            self.reset_buttons.append((profile, Button(
                rect, "Reset Progress", lambda p=profile: self._reset_progress(p),
                self.ctx.resources, bg_color=theme.COLOR_ERROR, font_size=theme.FONT_SIZE_SMALL)))
            y += 60

    def _try_pin(self) -> None:
        if self.ctx.config.verify_pin(self.pin_input.text):
            self.authenticated = True
            self.error = ""
        else:
            self.error = "Incorrect PIN"
        self.pin_input.text = ""

    def _reset_progress(self, profile) -> None:
        """Transactional reset: wipes this student's attempts/progress/badges,
        keeps their profile row (name/avatar) so they don't have to re-create it."""
        self.ctx.db.begin()
        try:
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
            self.ctx.db.commit()
        except Exception:
            self.ctx.db.rollback()
            raise

    def handle_event(self, event) -> None:
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

        for _, btn in self.reset_buttons:
            if btn.handle_event(event):
                return

    def update(self, dt: float) -> None:
        if not self.authenticated:
            self.pin_input.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        self.back_button.render(surface)

        if not self.authenticated:
            title = self.ctx.resources.text_surface("Teacher PIN", font_h, theme.COLOR_TEXT)
            surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 220)))
            self.pin_input.render(surface)
            self.submit_button.render(surface)
            if self.error:
                font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
                err_surf = self.ctx.resources.text_surface(self.error, font_small, theme.COLOR_ERROR)
                surface.blit(err_surf, err_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 420)))
            return

        title = self.ctx.resources.text_surface("Class Overview", font_h, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 60)))

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        y = 160
        for profile, btn in self.reset_buttons:
            line = f"{profile.name} — Level {profile.level}, streak {profile.current_streak}d"
            surf = self.ctx.resources.text_surface(line, font_body, theme.COLOR_TEXT)
            surface.blit(surf, (80, y))
            btn.render(surface)
            y += 60
