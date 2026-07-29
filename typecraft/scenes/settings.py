"""scenes/settings.py — volume, mute, and set-teacher-PIN."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button
from typecraft.ui.progress_bar import ProgressBar
from typecraft.ui.text_input import TextInput


class SettingsScene(Scene):
    def on_enter(self, **kwargs) -> None:
        cx = theme.SCREEN_WIDTH // 2
        self.back_button = Button(pygame.Rect(20, 20, 100, 44), "Back",
                                   lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
                                   bg_color=theme.COLOR_TEXT_MUTED)

        self.volume_bar = ProgressBar(pygame.Rect(cx - 150, 220, 300, 24))
        self.volume_bar.set_value(0.7)
        self.vol_down = Button(pygame.Rect(cx - 220, 210, 50, 44), "-", self._vol_down, self.ctx.resources)
        self.vol_up = Button(pygame.Rect(cx + 170, 210, 50, 44), "+", self._vol_up, self.ctx.resources)

        self.muted = False
        self.mute_button = Button(pygame.Rect(cx - 90, 280, 180, 46), "Mute", self._toggle_mute,
                                   self.ctx.resources)

        self.pin_input = TextInput(pygame.Rect(cx - 100, 420, 200, 44), self.ctx.resources,
                                    placeholder="New 4-digit PIN", max_length=4, is_password=True)
        self.set_pin_button = Button(pygame.Rect(cx - 90, 480, 180, 46), "Set Teacher PIN",
                                      self._set_pin, self.ctx.resources)
        self.pin_status = ""

    def _vol_down(self) -> None:
        v = max(0.0, self.volume_bar.value - 0.1)
        self.volume_bar.set_value(v)
        self.ctx.audio.set_volume(v)

    def _vol_up(self) -> None:
        v = min(1.0, self.volume_bar.value + 0.1)
        self.volume_bar.set_value(v)
        self.ctx.audio.set_volume(v)

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self.ctx.audio.set_muted(self.muted)
        self.mute_button.label = "Unmute" if self.muted else "Mute"

    def _set_pin(self) -> None:
        pin = self.pin_input.text.strip()
        if len(pin) == 4 and pin.isdigit():
            self.ctx.config.set_pin(pin)
            self.pin_status = "PIN updated."
        else:
            self.pin_status = "PIN must be 4 digits."
        self.pin_input.text = ""

    def handle_event(self, event) -> None:
        if self.back_button.handle_event(event):
            return
        if self.vol_down.handle_event(event):
            return
        if self.vol_up.handle_event(event):
            return
        if self.mute_button.handle_event(event):
            return
        if self.pin_input.handle_event(event):
            return
        if self.set_pin_button.handle_event(event):
            return

    def update(self, dt: float) -> None:
        self.pin_input.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        title = self.ctx.resources.text_surface("Settings", font_h, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 100)))

        self.back_button.render(surface)
        self.volume_bar.render(surface)
        self.vol_down.render(surface)
        self.vol_up.render(surface)
        self.mute_button.render(surface)
        self.pin_input.render(surface)
        self.set_pin_button.render(surface)

        if self.pin_status:
            font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
            status_surf = self.ctx.resources.text_surface(
                self.pin_status, font_small, theme.COLOR_PRIMARY_DARK)
            surface.blit(status_surf, status_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 540)))
