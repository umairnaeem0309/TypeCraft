"""ui/text_input.py — simple single-line text entry widget (profile names, PIN)."""

import pygame

from typecraft.ui import theme
from typecraft.ui.widget import Widget


class TextInput(Widget):
    def __init__(self, rect, resource_manager, placeholder="", max_length=20, is_password=False):
        super().__init__(rect)
        self.resources = resource_manager
        self.placeholder = placeholder
        self.max_length = max_length
        self.is_password = is_password
        self.text = ""
        self.focused = False
        self._cursor_visible = True
        self._cursor_timer = 0.0

    def handle_event(self, event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
            return self.focused
        if not self.focused:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.focused = False
            elif event.unicode and event.unicode.isprintable() and len(self.text) < self.max_length:
                self.text += event.unicode
            return True
        return False

    def update(self, dt: float) -> None:
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def render(self, surface) -> None:
        if not self.visible:
            return
        border_color = theme.COLOR_ACCENT if self.focused else theme.COLOR_TEXT_MUTED
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=6)

        font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        display_text = ("*" * len(self.text)) if self.is_password else self.text
        if display_text:
            text_surf = self.resources.text_surface(display_text, font, theme.COLOR_TEXT)
        else:
            text_surf = self.resources.text_surface(self.placeholder, font, theme.COLOR_TEXT_MUTED)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.centery - text_surf.get_height() // 2))

        if self.focused and self._cursor_visible:
            cursor_x = self.rect.x + 10 + (text_surf.get_width() if display_text else 0)
            pygame.draw.line(surface, theme.COLOR_TEXT,
                              (cursor_x, self.rect.y + 8), (cursor_x, self.rect.bottom - 8), 2)
