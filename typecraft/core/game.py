"""
core/game.py

Owns the window and the 30 FPS Event -> Update -> Render loop (§1.3).
Contains zero screen-specific logic — every phase is forwarded to the
active scene through GameStateManager. Defaults to a full-screen flip
with a double-buffered display; pass full_repaint=False to use the
experimental dirty-rect mode instead.
"""

import time
from typing import List

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
    def __init__(self, *, full_repaint: bool = True, profile: bool = False,
                 profile_path: str = "typecraft_profile.csv"):
        pygame.init()
        # Double-buffered display gives clean full-frame flips and eliminates the
        # tearing/flicker that can happen with partial dirty-rect updates.
        # SCALED keeps the internal coordinate space at 1280x720 and automatically
        # scales the output to the actual window/pixel size, so every scene and UI
        # widget keeps its hard-coded coordinates without refactoring. RESIZABLE
        # lets the user resize the window at runtime while PyGame handles scaling.
        self.screen = pygame.display.set_mode(
            (theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT),
            pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption("TypeCraft")
        self.clock = pygame.time.Clock()

        self.ctx = AppContext()
        self.states = build_state_manager(self.ctx)
        self.states.change("main_menu")
        self.notice_bar = NoticeBar(self.ctx)

        self.running = True
        self.full_repaint = full_repaint
        self.profile = profile
        self._profile_file = profile_path
        self._profile_handle = None

    def run(self) -> None:
        self._maybe_open_profile()
        try:
            while self.running:
                dt = self.clock.tick(theme.FPS) / 1000.0
                t0 = time.perf_counter()
                self._process_events()
                t1 = time.perf_counter()
                self._update(dt)
                t2 = time.perf_counter()
                self._render()
                t3 = time.perf_counter()
                self._profile_row(t1 - t0, t2 - t1, t3 - t2)
        finally:
            self._maybe_close_profile()
        self._shutdown()

    def _maybe_open_profile(self) -> None:
        if not self.profile:
            return
        handle = open(self._profile_file, "w", newline="", encoding="utf-8")
        handle.write("events_ms,update_ms,render_ms,dirty_rect_count\n")
        self._profile_handle = handle

    def _maybe_close_profile(self) -> None:
        if self._profile_handle is not None:
            self._profile_handle.close()
            self._profile_handle = None

    def _profile_row(self, events_sec: float, update_sec: float, render_sec: float) -> None:
        if self._profile_handle is None:
            return
        scene = self.states.current
        dirty_count = len(scene.dirty_rects) if scene else 0
        self._profile_handle.write(
            f"{events_sec * 1000:.3f},{update_sec * 1000:.3f},"
            f"{render_sec * 1000:.3f},{dirty_count}\n")

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
        scene = self.states.current
        if self.full_repaint:
            self.screen.fill(theme.COLOR_BG)
            self.states.render(self.screen)
            self.notice_bar.render(self.screen)
            pygame.display.flip()
        else:
            dirty = self._collect_dirty_rects(scene)
            # Clear changed areas before redrawing so moving objects don't leave trails.
            for rect in dirty:
                self.screen.fill(theme.COLOR_BG, rect)
            self.states.render(self.screen)
            self.notice_bar.render(self.screen)
            if dirty:
                pygame.display.update(dirty)
            # Next frame starts clean.
            scene.dirty_rects.clear()
            self.notice_bar.dirty_rects.clear()

    def _collect_dirty_rects(self, scene) -> List[pygame.Rect]:
        """Merge scene and notice-bar dirty rects, defaulting to full screen."""
        rects = list(scene.dirty_rects)
        rects.extend(self.notice_bar.dirty_rects)
        if not rects:
            rects = [pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)]
        return rects

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
