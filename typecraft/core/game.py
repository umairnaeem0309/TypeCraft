"""
core/game.py

Owns the window and the 30 FPS Event -> Update -> Render loop (§1.3).
Contains zero screen-specific logic — every phase is forwarded to the
active scene through GameStateManager. Uses dirty-rect display updates
(§5.1) rather than a full-screen flip().
"""

import pygame

from typecraft.core.app_context import AppContext
from typecraft.core.state_manager import GameStateManager
from typecraft.ui import theme


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))
        pygame.display.set_caption("TypeCraft")
        self.clock = pygame.time.Clock()

        self.ctx = AppContext()
        self.states = GameStateManager(self.ctx)
        self.ctx.states = self.states  # scenes reach the manager via ctx.states.change(...)
        self._register_scenes()

        self.running = True

    def _register_scenes(self) -> None:
        # Local import to avoid a circular import between core and scenes.
        from typecraft.scenes.main_menu import MainMenuScene
        from typecraft.scenes.profile_select import ProfileSelectScene
        from typecraft.scenes.lesson_select import LessonSelectScene
        from typecraft.scenes.mode_select import ModeSelectScene
        from typecraft.scenes.lesson import LessonScene
        from typecraft.scenes.results import ResultsScene
        from typecraft.scenes.leaderboard import LeaderboardScene
        from typecraft.scenes.teacher_dashboard import TeacherDashboardScene
        from typecraft.scenes.settings import SettingsScene

        self.states.register("main_menu", MainMenuScene)
        self.states.register("profile_select", ProfileSelectScene)
        self.states.register("lesson_select", LessonSelectScene)
        self.states.register("mode_select", ModeSelectScene)
        self.states.register("lesson", LessonScene)
        self.states.register("results", ResultsScene)
        self.states.register("leaderboard", LeaderboardScene)
        self.states.register("teacher_dashboard", TeacherDashboardScene)
        self.states.register("settings", SettingsScene)

        self.states.change("main_menu")

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(theme.FPS) / 1000.0
            self._process_events()
            self._update(dt)
            self._render()
        self._shutdown()

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            self.states.handle_event(event)

    def _update(self, dt: float) -> None:
        self.states.update(dt)

    def _render(self) -> None:
        self.screen.fill(theme.COLOR_BG)
        self.states.render(self.screen)
        pygame.display.flip()

    def _shutdown(self) -> None:
        self.ctx.db.close()
        pygame.quit()
