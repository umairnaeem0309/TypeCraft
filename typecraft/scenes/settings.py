"""scenes/settings.py — volume, mute, and set-teacher-PIN."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import screen, theme
from typecraft.ui.button import Button
from typecraft.ui.progress_bar import ProgressBar
from typecraft.ui.text_input import TextInput


#: Two full-width cards instead of a narrow centred column. The controls used to
#: occupy roughly y 150-460 of a 720 px window in a 360 px-wide strip, so most of
#: the screen was empty while the controls themselves were small.
CARD_X = 140
CARD_W = theme.SCREEN_WIDTH - 2 * CARD_X
SOUND_CARD = pygame.Rect(CARD_X, 130, CARD_W, 250)
PIN_CARD = pygame.Rect(CARD_X, 410, CARD_W, 210)


class SettingsScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.back_button = screen.back_button(self.ctx, "main_menu")

        # --- Sound card ---------------------------------------------------
        # FR-131: show what is actually stored, not a hard-coded guess. These used
        # to be fixed at 0.7/unmuted, so the screen contradicted the running app and
        # nothing the teacher changed here survived a restart.
        row_y = SOUND_CARD.y + 96
        self.vol_down = Button(pygame.Rect(SOUND_CARD.x + 40, row_y, 72, 64), "-",
                               self._vol_down, self.ctx.resources,
                               font_size=theme.FONT_SIZE_HEADING)
        self.volume_bar = ProgressBar(pygame.Rect(SOUND_CARD.x + 136, row_y + 16, 560, 32))
        self.vol_up = Button(pygame.Rect(SOUND_CARD.x + 720, row_y, 72, 64), "+",
                             self._vol_up, self.ctx.resources,
                             font_size=theme.FONT_SIZE_HEADING)
        self.volume_bar.set_value(self.ctx.audio.volume)

        self.muted = self.ctx.audio.muted
        self.mute_button = Button(pygame.Rect(SOUND_CARD.x + 40, row_y + 84, 240, 60),
                                   "Unmute" if self.muted else "Mute",
                                   self._toggle_mute, self.ctx.resources,
                                   bg_color=theme.COLOR_WARNING if self.muted
                                   else theme.COLOR_PRIMARY)

        # --- Teacher PIN card ---------------------------------------------
        pin_row_y = PIN_CARD.y + 96
        self.pin_input = TextInput(pygame.Rect(PIN_CARD.x + 40, pin_row_y, 320, 60),
                                    self.ctx.resources, placeholder="New 4-digit PIN",
                                    max_length=4, is_password=True, on_submit=self._set_pin)
        self.set_pin_button = Button(pygame.Rect(PIN_CARD.x + 396, pin_row_y, 280, 60),
                                      "Set Teacher PIN", self._set_pin, self.ctx.resources,
                                      bg_color=theme.COLOR_ADMIN)
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
        # Amber while muted, so a silent machine is obvious at a glance.
        self.mute_button.bg_color = (theme.COLOR_WARNING if self.muted
                                     else theme.COLOR_PRIMARY)

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

    def _card(self, surface, rect, heading) -> None:
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, rect, border_radius=16)
        pygame.draw.rect(surface, theme.COLOR_LOCKED, rect, width=2, border_radius=16)
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        surf = self.ctx.resources.text_surface(heading, font_h, theme.COLOR_TEXT)
        surface.blit(surf, (rect.x + 40, rect.y + 32))

    def render(self, surface) -> None:
        font_title = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_PAGE_TITLE)
        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)

        title = self.ctx.resources.text_surface("Settings", font_title, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                     screen.TITLE_Y)))
        self.back_button.render(surface)

        self._card(surface, SOUND_CARD, "Sound")
        volume_label = self.ctx.resources.text_surface(
            f"Volume  {round(self.volume_bar.value * 100)}%", font_body, theme.COLOR_TEXT_MUTED)
        surface.blit(volume_label, (SOUND_CARD.x + 40, self.vol_down.rect.y - 34))
        self.vol_down.render(surface)
        self.volume_bar.render(surface)
        self.vol_up.render(surface)
        self.mute_button.render(surface)
        mute_note = self.ctx.resources.text_surface(
            "Sounds are off while muted." if self.muted else "Sounds are on.",
            font_body, theme.COLOR_TEXT_MUTED)
        surface.blit(mute_note, mute_note.get_rect(
            midleft=(self.mute_button.rect.right + 24, self.mute_button.rect.centery)))

        self._card(surface, PIN_CARD, "Teacher PIN")
        self.pin_input.render(surface)
        self.set_pin_button.render(surface)
        if self.pin_status:
            status_surf = self.ctx.resources.text_surface(
                self.pin_status, font_body, theme.COLOR_PRIMARY_DARK)
            surface.blit(status_surf, (PIN_CARD.x + 40, self.pin_input.rect.bottom + 16))
        else:
            hint = self.ctx.resources.text_surface(
                "Protects the Teacher Dashboard. Leave unset to keep it open.",
                font_body, theme.COLOR_TEXT_MUTED)
            surface.blit(hint, (PIN_CARD.x + 40, self.pin_input.rect.bottom + 16))

        # FR-134: a settings file that could not be read must say so, or the teacher
        # sees their choices silently reverting with no explanation.
        y = PIN_CARD.bottom + 24
        for notice in getattr(self.ctx, "notices", []):
            surf = self.ctx.resources.text_surface(notice, font_small, theme.COLOR_ERROR)
            surface.blit(surf, surf.get_rect(center=(theme.SCREEN_WIDTH // 2, y)))
            y += 26
