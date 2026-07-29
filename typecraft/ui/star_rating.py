"""ui/star_rating.py — 0-3 star display widget."""

import pygame

from typecraft.ui import theme
from typecraft.ui.widget import Widget


class StarRating(Widget):
    def __init__(self, rect, stars=0, star_size=32):
        super().__init__(rect)
        self.stars = stars
        self.star_size = star_size

    def handle_event(self, event) -> bool:
        return False

    def _draw_star(self, surface, center, size, filled) -> None:
        color = (255, 193, 7) if filled else theme.COLOR_LOCKED
        points = []
        import math
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            radius = size if i % 2 == 0 else size * 0.4
            points.append((center[0] + radius * math.cos(angle),
                            center[1] - radius * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)

    def render(self, surface) -> None:
        if not self.visible:
            return
        spacing = self.star_size * 2.4
        start_x = self.rect.centerx - spacing
        for i in range(3):
            cx = start_x + i * spacing
            self._draw_star(surface, (cx, self.rect.centery), self.star_size, i < self.stars)
