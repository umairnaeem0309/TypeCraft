"""scenes/main_menu.py — entry screen: Play / Leaderboard / Teacher Dashboard / Settings / Quit."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button


class MainMenuScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._showing_quit_popup = False

        cx = theme.SCREEN_WIDTH // 2
        w, h, gap = 520, 72, 26
        start_y = 240  # anchor below the larger title/subtitle

        # Buttons are arranged in the order requested by users.
        self.widgets = [
            Button(pygame.Rect(cx - w // 2, start_y, w, h), "PLAY",
                   lambda: self.ctx.states.change("profile_select"), self.ctx.resources,
                   bg_color=theme.COLOR_PRIMARY, font_size=theme.FONT_SIZE_HEADING),
            Button(pygame.Rect(cx - w // 2, start_y + (h + gap), w, h), "Leader",
                   lambda: self.ctx.states.change("leaderboard"), self.ctx.resources,
                   bg_color=theme.COLOR_ACCENT, font_size=theme.FONT_SIZE_HEADING),
            Button(pygame.Rect(cx - w // 2, start_y + 2 * (h + gap), w, h), "Teacher Dashboard",
                   lambda: self.ctx.states.change("teacher_dashboard"), self.ctx.resources,
                   bg_color=theme.COLOR_ADMIN, font_size=theme.FONT_SIZE_HEADING),
            Button(pygame.Rect(cx - w // 2, start_y + 3 * (h + gap), w, h), "Settings",
                   lambda: self.ctx.states.change("settings"), self.ctx.resources,
                   bg_color=theme.COLOR_NEUTRAL, font_size=theme.FONT_SIZE_HEADING),
            Button(pygame.Rect(cx - w // 2, start_y + 4 * (h + gap), w, h), "Quit",
                   self._ask_quit, self.ctx.resources,
                   bg_color=theme.COLOR_ERROR, font_size=theme.FONT_SIZE_HEADING),
        ]

        # Quit confirmation popup buttons.
        btn_w, btn_h = 160, 54
        popup_y = theme.SCREEN_HEIGHT // 2 + 40
        self.yes_button = Button(
            pygame.Rect(cx - btn_w - 20, popup_y, btn_w, btn_h), "Yes",
            self._confirm_quit, self.ctx.resources, bg_color=theme.COLOR_ERROR)
        self.no_button = Button(
            pygame.Rect(cx + 20, popup_y, btn_w, btn_h), "No",
            self._cancel_quit, self.ctx.resources, bg_color=theme.COLOR_TEXT_MUTED)

    def _ask_quit(self) -> None:
        self._showing_quit_popup = True

    def _confirm_quit(self) -> None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _cancel_quit(self) -> None:
        self._showing_quit_popup = False

    def handle_event(self, event) -> None:
        if self._showing_quit_popup:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_y:
                    self._confirm_quit()
                    return
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_n:
                    self._cancel_quit()
                    return
            if self.yes_button.handle_event(event):
                return
            if self.no_button.handle_event(event):
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._quit_popup_rect().collidepoint(event.pos):
                    self._cancel_quit()
            return

        for w in self.widgets:
            if w.handle_event(event):
                break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        # Use a larger title to fill the empty top space.
        font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TITLE + 12)
        title = self.ctx.resources.text_surface("TypeCraft", font, theme.COLOR_PRIMARY_DARK)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 110)))

        # Subtitle
        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        subtitle = self.ctx.resources.text_surface(
            "Learn to type, one key at a time", font_small, theme.COLOR_TEXT_MUTED)
        surface.blit(subtitle, subtitle.get_rect(center=(theme.SCREEN_WIDTH // 2, 170)))

        for w in self.widgets:
            w.render(surface)

        if self._showing_quit_popup:
            self._render_quit_popup(surface)

    def _quit_popup_rect(self) -> pygame.Rect:
        panel_w, panel_h = 460, 220
        return pygame.Rect(
            (theme.SCREEN_WIDTH - panel_w) // 2,
            (theme.SCREEN_HEIGHT - panel_h) // 2,
            panel_w, panel_h,
        )

    def _render_quit_popup(self, surface) -> None:
        # Dim the background so the popup stands out.
        shade = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surface.blit(shade, (0, 0))

        panel = self._quit_popup_rect()
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, panel, border_radius=16)
        pygame.draw.rect(surface, theme.COLOR_ERROR, panel, width=3, border_radius=16)

        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)

        heading = self.ctx.resources.text_surface("Quit TypeCraft?", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(panel.centerx, panel.y + 50)))

        body = self.ctx.resources.text_surface("Are you sure you want to exit?", font_body, theme.COLOR_TEXT_MUTED)
        surface.blit(body, body.get_rect(center=(panel.centerx, panel.y + 100)))

        self.yes_button.render(surface)
        self.no_button.render(surface)
