"""scenes/mode_select.py — pick the typing mode (D1) before a lesson starts."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button

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
        w, h, gap = 620, 86, 30
        start_y = 220

        # Give every mode a distinct color so no two look the same.
        mode_colors = [theme.COLOR_PRIMARY, theme.COLOR_ACCENT, theme.COLOR_WARNING]

        self.mode_buttons = []
        for i, mode_key in enumerate(MODE_ORDER):
            rect = pygame.Rect(cx - w // 2, start_y + i * (h + gap), w, h)
            btn = Button(rect, MODE_LABELS[mode_key],
                         lambda mk=mode_key: self._select_mode(mk), self.ctx.resources,
                         bg_color=mode_colors[i],
                         font_size=theme.FONT_SIZE_HEADING)
            self.mode_buttons.append(btn)

        self.back_button = Button(
            pygame.Rect(20, 20, 120, 50), "Back",
            lambda: self.ctx.states.change("lesson_select"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )
        # Reusable italic font for the page subtitle.
        self._subtitle_font = pygame.font.Font(None, theme.FONT_SIZE_HEADING)
        self._subtitle_font.set_italic(True)

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
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TITLE - 8)
        heading = self.ctx.resources.text_surface(self.lesson.title, font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                     self.back_button.rect.centery + 8)))

        sub = self.ctx.resources.text_surface("Choose a typing mode", self._subtitle_font, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, 108)))

        # Draw a subtle panel behind the mode buttons.
        if self.mode_buttons:
            pad = 28
            top = self.mode_buttons[0].rect.top - pad
            bottom = self.mode_buttons[-1].rect.bottom + pad
            panel = pygame.Rect(theme.SCREEN_WIDTH // 2 - 360, top, 720, bottom - top)
            pygame.draw.rect(surface, theme.COLOR_CARD_BG, panel, border_radius=16)
            pygame.draw.rect(surface, theme.COLOR_LOCKED, panel, width=2, border_radius=16)

        for btn in self.mode_buttons:
            btn.render(surface)
        self.back_button.render(surface)
