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
            pygame.Rect(20, 20, 100, 44), "Back",
            lambda: self.ctx.states.change("main_menu"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )
        self.wpm_tab_btn = Button(pygame.Rect(theme.SCREEN_WIDTH // 2 - 210, 100, 200, 46),
                                   "Top Net WPM", lambda: self._set_tab(TAB_WPM), self.ctx.resources)
        self.acc_tab_btn = Button(pygame.Rect(theme.SCREEN_WIDTH // 2 + 10, 100, 200, 46),
                                   "Top Accuracy", lambda: self._set_tab(TAB_ACCURACY),
                                   self.ctx.resources, bg_color=theme.COLOR_ACCENT)
        self._load_rows()

    def _set_tab(self, tab: str) -> None:
        self.tab = tab
        self._load_rows()

    def _load_rows(self) -> None:
        column = "best_wpm_net" if self.tab == TAB_WPM else "best_accuracy"
        self.rows = self.ctx.db.query(
            f"""SELECT p.name as name, MAX(lp.{column}) as score
                FROM lesson_progress lp
                JOIN profiles p ON p.id = lp.profile_id
                GROUP BY lp.profile_id
                ORDER BY score DESC
                LIMIT 10"""
        )

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
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        title = self.ctx.resources.text_surface("Leaderboard", font_h, theme.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 50)))

        self.wpm_tab_btn.render(surface)
        self.acc_tab_btn.render(surface)
        self.back_button.render(surface)

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        y = 190
        unit = "wpm" if self.tab == TAB_WPM else "%"
        for i, row in enumerate(self.rows, start=1):
            line = f"{i}. {row['name']} — {row['score']:.0f} {unit}"
            surf = self.ctx.resources.text_surface(line, font_body, theme.COLOR_TEXT)
            surface.blit(surf, (theme.SCREEN_WIDTH // 2 - 200, y))
            y += 40

        if not self.rows:
            empty = self.ctx.resources.text_surface(
                "No completed lessons yet.", font_body, theme.COLOR_TEXT_MUTED)
            surface.blit(empty, empty.get_rect(center=(theme.SCREEN_WIDTH // 2, 300)))
