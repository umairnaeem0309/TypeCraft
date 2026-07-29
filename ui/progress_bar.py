"""ui/progress_bar.py — simple horizontal progress bar (used for XP / lesson progress)."""

import pygame

from TypeCraft.ui import theme
from TypeCraft.ui.widget import Widget


class ProgressBar(Widget):
    def __init__(self, rect, fg_color=None, bg_color=None):
        super().__init__(rect)
        self.fg_color = fg_color or theme.COLOR_PRIMARY
        self.bg_color = bg_color or theme.COLOR_LOCKED
        self.value = 0.0  # 0.0 - 1.0

    def handle_event(self, event) -> bool:
        return False

    def set_value(self, value: float) -> None:
        self.value = max(0.0, min(1.0, value))

    def render(self, surface) -> None:
        if not self.visible:
            return
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=self.rect.height // 2)
        fill_width = int(self.rect.width * self.value)
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, self.fg_color, fill_rect, border_radius=self.rect.height // 2)
