"""ui/hud.py — live WPM/accuracy/combo/timer/mistakes readout during a lesson.
Per §5.5, values are only recomputed when the engine reports a change, not
blindly every frame — the scene is responsible for calling update_metrics()
only after a keystroke."""

import pygame

from TypeCraft.ui import theme
from TypeCraft.ui.widget import Widget


class HUD(Widget):
    def __init__(self, rect, resource_manager):
        super().__init__(rect)
        self.resources = resource_manager
        self._metrics = {"wpm_net": 0.0, "wpm_gross": 0.0, "accuracy": 0.0,
                          "combo": 0, "errors": 0, "elapsed_sec": 0.0}

    def handle_event(self, event) -> bool:
        return False

    def update_metrics(self, metrics: dict) -> None:
        self._metrics = metrics

    def render(self, surface) -> None:
        if not self.visible:
            return
        font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        m = self._metrics
        items = [
            f"WPM {m['wpm_net']:.0f}",
            f"Accuracy {m['accuracy']:.0f}%",
            f"Combo {m['combo']}",
            f"Mistakes {m['errors']}",
            f"Time {m['elapsed_sec']:.0f}s",
        ]
        x = self.rect.x
        for item in items:
            surf = self.resources.text_surface(item, font, theme.COLOR_TEXT)
            surface.blit(surf, (x, self.rect.y))
            x += surf.get_width() + 30
