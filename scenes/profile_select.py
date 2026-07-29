"""scenes/profile_select.py — pick or create a student profile."""

import pygame

from TypeCraft.core.scene import Scene
from TypeCraft.ui import theme
from TypeCraft.ui.button import Button
from TypeCraft.ui.text_input import TextInput

AVATARS = ["avatar_fox", "avatar_owl", "avatar_cat", "avatar_bear"]


class ProfileSelectScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.profiles = self.ctx.profiles.list_all()
        self.name_input = TextInput(pygame.Rect(theme.SCREEN_WIDTH // 2 - 150, 550, 300, 44),
                                     self.ctx.resources, placeholder="New student name")
        self.create_button = Button(
            pygame.Rect(theme.SCREEN_WIDTH // 2 - 90, 610, 180, 46),
            "Create Profile", self._create_profile, self.ctx.resources,
        )
        self.back_button = Button(
            pygame.Rect(20, 20, 100, 44), "Back",
            lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )
        self._build_profile_buttons()

    def _build_profile_buttons(self) -> None:
        self.profile_buttons = []
        cols = 4
        card_w, card_h, gap = 220, 140, 24
        start_x = (theme.SCREEN_WIDTH - (cols * card_w + (cols - 1) * gap)) // 2
        for i, profile in enumerate(self.profiles):
            row, col = divmod(i, cols)
            x = start_x + col * (card_w + gap)
            y = 160 + row * (card_h + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.profile_buttons.append((profile, rect))

    def _create_profile(self) -> None:
        name = self.name_input.text.strip()
        if not name:
            return
        avatar = AVATARS[len(self.profiles) % len(AVATARS)]
        self.ctx.profiles.create(name, avatar)
        self.name_input.text = ""
        self.profiles = self.ctx.profiles.list_all()
        self._build_profile_buttons()

    def _select_profile(self, profile) -> None:
        self.ctx.active_profile = profile
        self.ctx.states.change("lesson_select")

    def handle_event(self, event) -> None:
        if self.back_button.handle_event(event):
            return
        if self.name_input.handle_event(event):
            return
        if self.create_button.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for profile, rect in self.profile_buttons:
                if rect.collidepoint(event.pos):
                    self._select_profile(profile)
                    return

    def update(self, dt: float) -> None:
        self.name_input.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        heading = self.ctx.resources.text_surface("Who's playing?", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(theme.SCREEN_WIDTH // 2, 90)))

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        for profile, rect in self.profile_buttons:
            pygame.draw.rect(surface, theme.COLOR_CARD_BG, rect, border_radius=14)
            pygame.draw.rect(surface, theme.COLOR_PRIMARY, rect, width=2, border_radius=14)
            name_surf = self.ctx.resources.text_surface(profile.name, font_body, theme.COLOR_TEXT)
            surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.centery - 15)))
            lvl_surf = self.ctx.resources.text_surface(
                f"Level {profile.level}", font_body, theme.COLOR_TEXT_MUTED)
            surface.blit(lvl_surf, lvl_surf.get_rect(center=(rect.centerx, rect.centery + 25)))

        self.name_input.render(surface)
        self.create_button.render(surface)
        self.back_button.render(surface)
