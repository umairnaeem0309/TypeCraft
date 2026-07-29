"""scenes/mode_select.py — pick the typing mode (D1) before a lesson starts."""

import pygame

from TypeCraft.core.scene import Scene
from TypeCraft.ui import theme
from TypeCraft.ui.button import Button

MODE_LABELS = {
    "lock_on_error": "Lock on Error (beginner)",
    "backspace": "Backspace Allowed",
    "free_advance": "Free Advance (speed drill)",
}
MODE_ORDER = ["lock_on_error", "backspace", "free_advance"]


class ModeSelectScene(Scene):
    def on_enter(self, lesson=None, **kwargs) -> None:
        self.lesson = lesson
        cx = theme.SCREEN_WIDTH // 2
        w, h, gap = 340, 60, 20
        start_y = 260

        self.mode_buttons = []
        for i, mode_key in enumerate(MODE_ORDER):
            rect = pygame.Rect(cx - w // 2, start_y + i * (h + gap), w, h)
            is_default = mode_key == lesson.default_mode
            btn = Button(rect, MODE_LABELS[mode_key],
                         lambda mk=mode_key: self._select_mode(mk), self.ctx.resources,
                         bg_color=theme.COLOR_PRIMARY if is_default else theme.COLOR_ACCENT)
            self.mode_buttons.append(btn)

        self.back_button = Button(
            pygame.Rect(20, 20, 100, 44), "Back",
            lambda: self.ctx.states.change("lesson_select"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )

    def _select_mode(self, mode_key: str) -> None:
        self.ctx.states.change("lesson", lesson=self.lesson, mode_key=mode_key)

    def handle_event(self, event) -> None:
        if self.back_button.handle_event(event):
            return
        for btn in self.mode_buttons:
            if btn.handle_event(event):
                return

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        heading = self.ctx.resources.text_surface(self.lesson.title, font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(theme.SCREEN_WIDTH // 2, 140)))

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        sub = self.ctx.resources.text_surface("Choose a typing mode", font_small, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, 190)))

        for btn in self.mode_buttons:
            btn.render(surface)
        self.back_button.render(surface)
