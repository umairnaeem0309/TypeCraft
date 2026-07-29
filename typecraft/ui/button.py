"""ui/button.py — clickable button widget."""

import pygame

from typecraft.ui import theme
from typecraft.ui.widget import Widget


class Button(Widget):
    def __init__(self, rect, label, on_click, resource_manager,
                 bg_color=None, text_color=None, font_size=theme.FONT_SIZE_BODY,
                 enabled=True):
        super().__init__(rect)
        self.label = label
        self.on_click = on_click
        self.resources = resource_manager
        self.bg_color = bg_color or theme.COLOR_PRIMARY
        self.text_color = text_color or theme.COLOR_BUTTON_TEXT
        self.font_size = font_size
        self.enabled = enabled
        self._hovered = False

    def handle_event(self, event) -> bool:
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def render(self, surface) -> None:
        if not self.visible:
            return
        color = self.bg_color if self.enabled else theme.COLOR_LOCKED
        if self._hovered and self.enabled:
            color = tuple(max(0, c - 20) for c in color)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)

        font = self.resources.font(theme.FONT_DEFAULT, self.font_size)
        text_surf = self.resources.text_surface(self.label, font, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
