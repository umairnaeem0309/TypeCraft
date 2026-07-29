"""
ui/keyboard_renderer.py

Static on-screen QWERTY keyboard with 8-finger colour coding. Per §5.3,
the whole keyboard is pre-rendered ONCE to a base surface at scene entry;
per frame we blit that base once and overlay only the single highlighted
key — never redraw 40+ keys individually per frame.
"""

import pygame

from typecraft.ui import theme

ROWS = [
    list("1234567890"),
    list("qwertyuiop"),
    list("asdfghjkl;"),
    list("zxcvbnm,./"),
]

KEY_FINGER = {
    "1": "left_pinky", "2": "left_pinky", "3": "left_ring", "4": "left_index", "5": "left_index",
    "6": "right_index", "7": "right_index", "8": "right_middle", "9": "right_ring", "0": "right_pinky",
    "q": "left_pinky", "w": "left_ring", "e": "left_middle", "r": "left_index", "t": "left_index",
    "y": "right_index", "u": "right_index", "i": "right_middle", "o": "right_ring", "p": "right_pinky",
    "a": "left_pinky", "s": "left_ring", "d": "left_middle", "f": "left_index", "g": "left_index",
    "h": "right_index", "j": "right_index", "k": "right_middle", "l": "right_ring", ";": "right_pinky",
    "z": "left_pinky", "x": "left_ring", "c": "left_middle", "v": "left_index", "b": "left_index",
    "n": "right_index", "m": "right_index", ",": "right_middle", ".": "right_ring", "/": "right_pinky",
}

KEY_W, KEY_H, GAP = 56, 56, 6


class KeyboardRenderer:
    def __init__(self, resource_manager, origin=(0, 0)):
        self.resources = resource_manager
        self.origin = origin
        self.key_rects = {}
        self.finger_colors = theme.FINGER_COLORS
        self.base_layer = None
        self._active_key = None

    def prerender(self) -> None:
        width = len(ROWS[0]) * (KEY_W + GAP)
        height = len(ROWS) * (KEY_H + GAP)
        self.base_layer = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()

        font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        self.key_rects = {}
        for row_i, row in enumerate(ROWS):
            offset = (row_i * KEY_W * 0.4)
            for col_i, key in enumerate(row):
                x = offset + col_i * (KEY_W + GAP)
                y = row_i * (KEY_H + GAP)
                rect = pygame.Rect(int(x), int(y), KEY_W, KEY_H)
                finger = KEY_FINGER.get(key, "right_index")
                color = self.finger_colors[finger]
                pygame.draw.rect(self.base_layer, color, rect, border_radius=8)
                pygame.draw.rect(self.base_layer, theme.COLOR_TEXT, rect, width=2, border_radius=8)
                label = self.resources.text_surface(key.upper(), font, theme.COLOR_BUTTON_TEXT)
                self.base_layer.blit(label, label.get_rect(center=rect.center))
                self.key_rects[key] = rect

    def highlight(self, key: str, finger: str = None) -> None:
        self._active_key = key.lower() if key else None

    def render(self, surface) -> None:
        if self.base_layer is None:
            self.prerender()
        surface.blit(self.base_layer, self.origin)

        if self._active_key and self._active_key in self.key_rects:
            rect = self.key_rects[self._active_key].move(self.origin)
            pygame.draw.rect(surface, theme.COLOR_ACCENT, rect, width=4, border_radius=8)
