"""
core/game.py

Owns the window and the 30 FPS Event -> Update -> Render loop (§1.3).
Contains zero screen-specific logic — every phase is forwarded to the
active scene through GameStateManager. Uses dirty-rect display updates
(§5.1) rather than a full-screen flip().
"""

import pygame

from typecraft.core.app_context import AppContext
from typecraft.core.logging_setup import get_logger
from typecraft.core.state_manager import GameStateManager
from typecraft.ui import theme
from typecraft.ui.notice import NoticeBar


def build_state_manager(ctx) -> GameStateManager:
    """Register every scene and wire the manager onto the context.

    Module-level rather than a Game method so tests can obtain a fully-wired
    manager without opening a window, and so there is exactly one list of scene
    names in the codebase.

    Does not activate a scene — the caller chooses the entry point.
    """
    # Local imports avoid a circular import between core and scenes.
    from typecraft.scenes.main_menu import MainMenuScene
    from typecraft.scenes.profile_select import ProfileSelectScene
    from typecraft.scenes.lesson_select import LessonSelectScene
    from typecraft.scenes.mode_select import ModeSelectScene
    from typecraft.scenes.lesson import LessonScene
    from typecraft.scenes.results import ResultsScene
    from typecraft.scenes.leaderboard import LeaderboardScene
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene
    from typecraft.scenes.settings import SettingsScene

    states = GameStateManager(ctx)
    for name, scene_cls in (
        ("main_menu", MainMenuScene),
        ("profile_select", ProfileSelectScene),
        ("lesson_select", LessonSelectScene),
        ("mode_select", ModeSelectScene),
        ("lesson", LessonScene),
        ("results", ResultsScene),
        ("leaderboard", LeaderboardScene),
        ("teacher_dashboard", TeacherDashboardScene),
        ("settings", SettingsScene),
    ):
        states.register(name, scene_cls)

    ctx.states = states  # scenes reach the manager via ctx.states.change(...)
    return states


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))
        pygame.display.set_caption("TypeCraft")
        self.clock = pygame.time.Clock()

        self.ctx = AppContext()
        self.states = build_state_manager(self.ctx)
        self.states.change("main_menu")
        self.notice_bar = NoticeBar(self.ctx)

        self.running = True

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
                self._request_quit()
                return
            # Let the notice bar see clicks first so a warning strip can be
            # dismissed even if a scene button sits underneath it.
            if self.notice_bar.handle_event(event):
                continue
            self.states.handle_event(event)

    def _update(self, dt: float) -> None:
        self.states.update(dt)

    def _render(self) -> None:
        self.screen.fill(theme.COLOR_BG)
        self.states.render(self.screen)
        self.notice_bar.render(self.screen)
        pygame.display.flip()

    def _request_quit(self) -> None:
        """Window close: give the active scene a chance to save before we stop.

        Without this the loop simply ended and a lesson in progress was discarded
        (defect D-06). The save is wrapped because a failure here must still let
        the application exit — a hung window is worse than a lost attempt, and the
        checkpoint from TC-009 already limits the loss to a few seconds.
        """
        try:
            self.states.notify_quit()
        except Exception:
            get_logger(__name__).exception("failed to save state while closing")
        self.running = False

    def _shutdown(self) -> None:
        self.ctx.db.close()
        pygame.quit()
