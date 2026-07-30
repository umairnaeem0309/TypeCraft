"""scenes/leaderboard.py — ranks on best net WPM and a separate accuracy board.
Completed attempts only (§2.2 status filter rule) — LESSON_PROGRESS cache
already stores each profile's best, so we read that instead of scanning
every attempt row."""

import pygame

from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button

TAB_WPM = "wpm"
TAB_ACCURACY = "accuracy"


class LeaderboardScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.tab = TAB_WPM
        self.back_button = Button(
            pygame.Rect(20, 20, 120, 50), "Back",
            lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )
        self.wpm_tab_btn = Button(pygame.Rect(theme.SCREEN_WIDTH // 2 - 290, 170, 280, 64),
                                   "Top Net WPM", lambda: self._set_tab(TAB_WPM), self.ctx.resources,
                                   font_size=theme.FONT_SIZE_HEADING)
        self.acc_tab_btn = Button(pygame.Rect(theme.SCREEN_WIDTH // 2 + 10, 170, 280, 64),
                                   "Top Accuracy", lambda: self._set_tab(TAB_ACCURACY),
                                   self.ctx.resources, bg_color=theme.COLOR_ACCENT,
                                   font_size=theme.FONT_SIZE_HEADING)
        # Reusable italic fonts for subtitle and bottom note.
        self._subtitle_font = pygame.font.Font(None, theme.FONT_SIZE_HEADING)
        self._subtitle_font.set_italic(True)
        self._note_font = pygame.font.Font(None, theme.FONT_SIZE_BODY)
        self._note_font.set_italic(True)
        self._load_rows()

    def _set_tab(self, tab: str) -> None:
        self.tab = tab
        self._load_rows()

    def _load_rows(self) -> None:
        # The query lives in ProgressionService: it is a rule about which attempts
        # count, not a display concern, and it needs to be testable without a window.
        self.rows = self.ctx.progression.leaderboard(self.tab)

    def handle_event(self, event) -> None:
        if self.back_button.handle_event(event):
            return
        if self.wpm_tab_btn.handle_event(event):
            return
        if self.acc_tab_btn.handle_event(event):
            return

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TITLE - 8)
        title = self.ctx.resources.text_surface("Leaderboard", font_h, theme.COLOR_TEXT)
        # Keep the heading slightly below the Back button's centre.
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                     self.back_button.rect.centery + 8)))

        sub = self.ctx.resources.text_surface(
            "Top students by speed or accuracy", self._subtitle_font, theme.COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(theme.SCREEN_WIDTH // 2, 105)))

        self.wpm_tab_btn.render(surface)
        self.acc_tab_btn.render(surface)
        self.back_button.render(surface)

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        y = 250
        row_height = 42
        row_gap = 2
        unit = "wpm" if self.tab == TAB_WPM else "%"
        for i, row in enumerate(self.rows, start=1):
            row_rect = pygame.Rect(theme.SCREEN_WIDTH // 2 - 380, y - 6, 760, row_height)
            if i % 2 == 0:
                pygame.draw.rect(surface, (240, 242, 245), row_rect, border_radius=10)
            line = f"{i}. {row['name']} — {row['score']:.0f} {unit}"
            surf = self.ctx.resources.text_surface(line, font_body, theme.COLOR_TEXT)
            surface.blit(surf, (row_rect.x + 28, row_rect.centery - surf.get_height() // 2))
            y += row_height + row_gap

        if not self.rows:
            empty = self.ctx.resources.text_surface(
                "No completed lessons yet.", font_body, theme.COLOR_TEXT_MUTED)
            surface.blit(empty, empty.get_rect(center=(theme.SCREEN_WIDTH // 2, 400)))
            return

        # FR-113: the tie rule is stated on screen so a child can see why two equal
        # scores are ordered the way they are.
        note = self.ctx.resources.text_surface(
            "Best score per student, completed lessons only. Equal scores: longest-joined first.",
            self._note_font, theme.COLOR_TEXT_MUTED)
        surface.blit(note, note.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                 theme.SCREEN_HEIGHT - 30)))
