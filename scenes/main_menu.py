"""scenes/main_menu.py — entry screen: Play / Leaderboard / Settings / Teacher."""

import pygame

from TypeCraft.core.scene import Scene
from TypeCraft.ui import theme
from TypeCraft.ui.button import Button


class MainMenuScene(Scene):
    def on_enter(self, **kwargs) -> None:
        cx = theme.SCREEN_WIDTH // 2
        w, h, gap = 280, 60, 20
        start_y = 300

        self.widgets = [
            Button(pygame.Rect(cx - w // 2, start_y, w, h), "Play",
                   lambda: self.ctx.states.change("profile_select"), self.ctx.resources),
            Button(pygame.Rect(cx - w // 2, start_y + (h + gap), w, h), "Leaderboard",
                   lambda: self.ctx.states.change("leaderboard"), self.ctx.resources,
                   bg_color=theme.COLOR_ACCENT),
            Button(pygame.Rect(cx - w // 2, start_y + 2 * (h + gap), w, h), "Settings",
                   lambda: self.ctx.states.change("settings"), self.ctx.resources,
                   bg_color=theme.COLOR_TEXT_MUTED),
            Button(pygame.Rect(cx - w // 2, start_y + 3 * (h + gap), w, h), "Teacher Dashboard",
                   lambda: self.ctx.states.change("teacher_dashboard"), self.ctx.resources,
                   bg_color=theme.COLOR_PRIMARY_DARK),
        ]

    def handle_event(self, event) -> None:
        for w in self.widgets:
            if w.handle_event(event):
                break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TITLE)
        title = self.ctx.resources.text_surface("TypeCraft", font, theme.COLOR_PRIMARY_DARK)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 180)))
        for w in self.widgets:
            w.render(surface)
