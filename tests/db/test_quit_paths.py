"""The three ways a lesson can end (FR-070, FR-071, FR-072, FR-076).

Completion, Escape, and closing the window must all persist exactly one row and
agree on what it contains. Window-close used to persist nothing at all: `Game`
handled `pygame.QUIT` by setting `running = False` and returning, so the active
scene was never told (defect D-06).
"""

import pygame
import pytest

from typecraft.models.attempt import AttemptStatus
from typecraft.scenes.lesson import LessonScene


@pytest.fixture
def lesson_scene(app_ctx, display):
    student = app_ctx.profiles.create("Quitter", "avatar_cat")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="free_advance")
    return app_ctx, scene, lesson


def attempts(ctx):
    return ctx.db.query("SELECT * FROM lesson_attempts ORDER BY id")


def type_keys(scene, count):
    text = scene.engine.target
    for ch in text[:count]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))


# --------------------------------------------------------------------- window close

def test_closing_the_window_mid_lesson_saves_an_incomplete_attempt(lesson_scene):
    """FR-071 — the defect D-06 regression test."""
    ctx, scene, _ = lesson_scene
    type_keys(scene, 5)
    assert attempts(ctx) == [], "nothing written yet: below the checkpoint interval"

    scene.on_quit_requested()

    rows = attempts(ctx)
    assert len(rows) == 1
    assert rows[0]["status"] == "incomplete"
    assert rows[0]["total_keystrokes"] == 5
    assert rows[0]["xp_awarded"] == 0 and rows[0]["stars"] == 0


def test_closing_the_window_before_typing_saves_nothing(lesson_scene):
    """FR-072: opening a lesson and changing your mind is not an attempt."""
    ctx, scene, _ = lesson_scene
    scene.on_quit_requested()
    assert attempts(ctx) == []


def test_closing_after_a_checkpoint_promotes_that_row(lesson_scene):
    """One attempt, one row — the checkpoint must not become a second attempt."""
    ctx, scene, _ = lesson_scene
    type_keys(scene, 4)
    scene.update(ctx.progression.CHECKPOINT_INTERVAL_SEC + 1)
    assert len(attempts(ctx)) == 1 and attempts(ctx)[0]["status"] == "in_progress"

    scene.on_quit_requested()

    rows = attempts(ctx)
    assert len(rows) == 1
    assert rows[0]["status"] == "incomplete"


def test_the_game_loop_notifies_the_scene_on_quit(app_ctx, display, monkeypatch):
    """The wiring itself: Game must call on_quit_requested() before stopping."""
    from typecraft.core.game import Game

    monkeypatch.setattr(pygame.display, "set_mode", lambda *a, **k: display)
    game = Game()
    try:
        called = []
        game.states.current.on_quit_requested = lambda: called.append(True)

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        game._process_events()

        assert called == [True], "the scene was never told the window was closing"
        assert game.running is False
    finally:
        game.ctx.db.close()


def test_a_failing_save_still_lets_the_application_exit(app_ctx, display, monkeypatch, caplog):
    """A hung window is worse than a lost attempt, and TC-009's checkpoint already
    limits the loss. The failure must be logged, not swallowed silently."""
    import logging

    from typecraft.core.game import Game

    monkeypatch.setattr(pygame.display, "set_mode", lambda *a, **k: display)
    game = Game()
    try:
        def explode():
            raise RuntimeError("disk full")

        game.states.current.on_quit_requested = explode

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        with caplog.at_level(logging.ERROR, logger="typecraft"):
            game._process_events()          # must not raise

        assert game.running is False
        assert any("disk full" in r.getMessage() or r.exc_info for r in caplog.records), \
            "the failure must be logged, not silently swallowed"
    finally:
        game.ctx.db.close()


# --------------------------------------------------------------------- escape & completion

def test_escape_mid_lesson_saves_an_incomplete_attempt(lesson_scene):
    """FR-070."""
    ctx, scene, _ = lesson_scene
    type_keys(scene, 3)

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))

    rows = attempts(ctx)
    assert len(rows) == 1
    assert rows[0]["status"] == "incomplete"
    assert rows[0]["total_keystrokes"] == 3


def test_escape_before_typing_saves_nothing(lesson_scene):
    """FR-072."""
    ctx, scene, _ = lesson_scene
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
    assert attempts(ctx) == []


def test_finishing_the_text_saves_one_complete_attempt(lesson_scene):
    ctx, scene, lesson = lesson_scene
    type_keys(scene, len(scene.engine.target))

    rows = attempts(ctx)
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"
    assert rows[0]["accuracy"] == pytest.approx(100.0)
    assert ctx.states.current.__class__.__name__ == "ResultsScene"


def test_all_three_exit_paths_agree_on_what_they_persist(app_ctx, display):
    """The reason `_finish()` is a single method: three call sites, one behaviour.
    Escape and window-close must produce identical rows for identical typing."""
    lesson = app_ctx.lessons.first_lesson()
    produced = []

    for exit_path in ("escape", "window_close"):
        student = app_ctx.profiles.create(f"S-{exit_path}", "avatar_bear")
        app_ctx.active_profile = student
        scene = LessonScene(app_ctx)
        scene.on_enter(lesson=lesson, mode_key="free_advance")
        type_keys(scene, 6)

        if exit_path == "escape":
            scene.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
        else:
            scene.on_quit_requested()

        row = app_ctx.db.query(
            "SELECT * FROM lesson_attempts WHERE profile_id=?", (student.id,))[0]
        produced.append({k: row[k] for k in
                         ("status", "total_keystrokes", "correct_keystrokes", "errors",
                          "stars", "xp_awarded", "mode", "lesson_id")})

    assert produced[0] == produced[1]
    assert produced[0]["status"] == "incomplete"


def test_an_incomplete_attempt_from_any_path_stays_out_of_aggregates(lesson_scene):
    """FR-076."""
    ctx, scene, _ = lesson_scene
    student = ctx.active_profile
    type_keys(scene, 5)
    scene.on_quit_requested()

    assert ctx.db.query("SELECT total_xp, level FROM profiles WHERE id=?",
                        (student.id,))[0] == {"total_xp": 0, "level": 1}
    assert ctx.db.query("SELECT COUNT(*) AS c FROM profile_badges")[0]["c"] == 0
    assert ctx.lessons.is_unlocked(student, "t1l2") is False
