"""ui/hud.py — live WPM/accuracy/combo/timer/mistakes readout during a lesson.

The HUD caches its rasterised surface and only re-creates it when the displayed
values actually change, so calling render() every frame is cheap."""

import pygame

from typecraft.ui import theme
from typecraft.ui.widget import Widget


class HUD(Widget):
    def __init__(self, rect, resource_manager):
        super().__init__(rect)
        self.resources = resource_manager
        self._metrics = {"wpm_net": 0.0, "wpm_gross": 0.0, "accuracy": 0.0,
                          "combo": 0, "errors": 0, "elapsed_sec": 0.0}
        self._display_texts = self._formatted_texts()
        self._cached_surf = None
        self._needs_rerender = True

    def handle_event(self, event) -> bool:
        return False

    def update_metrics(self, metrics: dict) -> None:
        self._metrics = metrics
        new_texts = self._formatted_texts()
        if new_texts != self._display_texts:
            self._display_texts = new_texts
            self._needs_rerender = True

    def _formatted_texts(self) -> tuple[str, ...]:
        m = self._metrics
        return (
            f"WPM {m['wpm_net']:.0f}",
            f"Accuracy {m['accuracy']:.0f}%",
            f"Combo {m['combo']}",
            f"Mistakes {m['errors']}",
            f"Time {m['elapsed_sec']:.0f}s",
        )

    def render(self, surface) -> None:
        if not self.visible:
            return
        if self._needs_rerender or self._cached_surf is None:
            self._cached_surf = self._render_to_surface()
            self._needs_rerender = False
        surface.blit(self._cached_surf, (self.rect.x, self.rect.y))

    def _render_to_surface(self):
        font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        items = self._display_texts
        total_width = 0
        height = 0
        text_surfs = []
        for item in items:
            surf = self.resources.text_surface(item, font, theme.COLOR_TEXT)
            text_surfs.append(surf)
            total_width += surf.get_width()
            height = max(height, surf.get_height())
        # Add gaps between items.
        gap = 30
        total_width += gap * (len(items) - 1)
        # A zero-sized surface is invalid; fall back to a single pixel so callers
        # can always blit it safely (e.g. a render before any metrics update).
        total_width = max(total_width, 1)
        height = max(height, 1)
        # Keep the dirty-rect footprint in sync with the real text size so scenes
        # that still use partial updates repaint the full HUD area.
        self.rect.width = total_width
        self.rect.height = height
        cached = pygame.Surface((total_width, height), pygame.SRCALPHA)
        x = 0
        for surf in text_surfs:
            cached.blit(surf, (x, 0))
            x += surf.get_width() + gap
        return cached
