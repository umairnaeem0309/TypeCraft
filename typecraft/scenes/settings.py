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
        self.back_button = Button(pygame.Rect(20, 20, 120, 50), "Back",
                                   lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
                                   bg_color=theme.COLOR_TEXT_MUTED)

        # FR-131: show what is actually stored, not a hard-coded guess. These used
        # to be fixed at 0.7/unmuted, so the screen contradicted the running app and
        # nothing the teacher changed here survived a restart.
        self.volume_bar = ProgressBar(pygame.Rect(cx - 180, 160, 360, 32))
        self.volume_bar.set_value(self.ctx.audio.volume)
        self.vol_down = Button(pygame.Rect(cx - 250, 151, 60, 50), "-", self._vol_down, self.ctx.resources)
        self.vol_up = Button(pygame.Rect(cx + 190, 151, 60, 50), "+", self._vol_up, self.ctx.resources)

        self.muted = self.ctx.audio.muted
        self.mute_button = Button(pygame.Rect(cx - 110, 230, 220, 54),
                                   "Unmute" if self.muted else "Mute",
                                   self._toggle_mute, self.ctx.resources)

        self.pin_input = TextInput(pygame.Rect(cx - 140, 340, 280, 52), self.ctx.resources,
                                    placeholder="New 4-digit PIN", max_length=4,
                                    is_password=True, on_submit=self._set_pin)
        self.set_pin_button = Button(pygame.Rect(cx - 110, 410, 220, 54), "Set Teacher PIN",
                                      self._set_pin, self.ctx.resources)
        self.pin_status = ""

    def _set_volume(self, value: float) -> None:
        """Apply to the running app *and* persist it (FR-132)."""
        value = round(max(0.0, min(1.0, value)), 2)
        self.volume_bar.set_value(value)
        self.ctx.audio.set_volume(value)
        self.ctx.config.set("volume", value)

    def _vol_down(self) -> None:
        self._set_volume(self.volume_bar.value - 0.1)

    def _vol_up(self) -> None:
        self._set_volume(self.volume_bar.value + 0.1)

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self.ctx.audio.set_muted(self.muted)
        self.ctx.config.set("muted", self.muted)
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
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, theme.LAYOUT_TITLE_Y)))

        self.back_button.render(surface)
        self.volume_bar.render(surface)
        self.vol_down.render(surface)
        self.vol_up.render(surface)
        self.mute_button.render(surface)
        self.pin_input.render(surface)
        self.set_pin_button.render(surface)

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)

        if self.pin_status:
            status_surf = self.ctx.resources.text_surface(
                self.pin_status, font_small, theme.COLOR_PRIMARY_DARK)
            surface.blit(status_surf, status_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 490)))

        # FR-134: a settings file that could not be read must say so, or the teacher
        # sees their choices silently reverting with no explanation.
        y = 530
        for notice in getattr(self.ctx, "notices", []):
            surf = self.ctx.resources.text_surface(notice, font_small, theme.COLOR_ERROR)
            surface.blit(surf, surf.get_rect(center=(theme.SCREEN_WIDTH // 2, y)))
            y += 24
