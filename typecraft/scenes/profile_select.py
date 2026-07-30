"""scenes/profile_select.py — pick or create a student profile."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button
from typecraft.ui.scroll_panel import ScrollPanel
from typecraft.ui.text_input import TextInput

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
        self.panel = ScrollPanel(pygame.Rect(0, 140, theme.SCREEN_WIDTH, 380))
        self._build_profile_buttons()

    def _build_profile_buttons(self) -> None:
        """Lay the cards out in content coordinates inside a scrolling viewport.

        Four across at a 164 px pitch used to run off the bottom of the window from
        the 9th child onward, so in a class of thirty most students simply could not
        be selected (FR-014).
        """
        self.profile_buttons = []
        cols = 4
        card_w, card_h, gap = 220, 140, 24
        start_x = (theme.SCREEN_WIDTH - (cols * card_w + (cols - 1) * gap)) // 2
        for i, profile in enumerate(self.profiles):
            row, col = divmod(i, cols)
            x = start_x + col * (card_w + gap)
            y = row * (card_h + gap)          # content space: first row at y = 0
            self.profile_buttons.append((profile, pygame.Rect(x, y, card_w, card_h)))

        rows = (len(self.profiles) + cols - 1) // cols
        self.panel.set_content_height(rows * (card_h + gap))

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
        if self.panel.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Hit-test in content space, so a scrolled click lands on the card the
            # teacher actually sees rather than the one that used to be there.
            local = self.panel.translated(event)
            if local is None:
                return
            for profile, rect in self.profile_buttons:
                if rect.collidepoint(local.pos):
                    self._select_profile(profile)
                    return

    def update(self, dt: float) -> None:
        self.name_input.update(dt)

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        heading = self.ctx.resources.text_surface("Who's playing?", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(theme.SCREEN_WIDTH // 2, 90)))

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        sub = self.ctx.resources.text_surface(
            "Select a student profile or create a new one", font_small, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, 125)))

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        mouse_pos = pygame.mouse.get_pos()
        with self.panel.clipped(surface):
            for profile, content_rect in self.profile_buttons:
                if not self.panel.is_visible(content_rect):
                    continue
                rect = self.panel.screen_rect(content_rect)
                hovered = rect.collidepoint(mouse_pos)
                bg = theme.COLOR_CARD_BG
                border = theme.COLOR_PRIMARY
                if hovered:
                    bg = (235, 248, 235)
                    border = theme.COLOR_PRIMARY_DARK
                pygame.draw.rect(surface, bg, rect, border_radius=14)
                pygame.draw.rect(surface, border, rect, width=3, border_radius=14)
                name_surf = self.ctx.resources.text_surface(profile.name, font_body, theme.COLOR_TEXT)
                surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.centery - 15)))
                lvl_surf = self.ctx.resources.text_surface(
                    f"Level {profile.level}", font_body, theme.COLOR_TEXT_MUTED)
                surface.blit(lvl_surf, lvl_surf.get_rect(center=(rect.centerx, rect.centery + 25)))
        self.panel.render_scrollbar(surface, theme.COLOR_PRIMARY, theme.COLOR_LOCKED)

        self.name_input.render(surface)
        self.create_button.render(surface)
        self.back_button.render(surface)
