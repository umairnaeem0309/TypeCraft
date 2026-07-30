"""Every scene can be entered, updated and rendered (FR-001..FR-006, AC-02).

The regression net TC-018's dirty-rect refactor needs before it touches the render
path (PLAN-02). Nine scenes exist; before this file, four of them
(`main_menu`, `mode_select`, `results`, and `lesson` end-to-end) had never been
constructed by a test at all, so a crash on entry would only have surfaced in front
of a class.

Runs headless under the dummy SDL driver, so it needs no display and no sound
device — the same conditions a school PC with a broken audio driver provides.
"""

import pygame
import pytest

from typecraft.core.game import build_state_manager
from typecraft.models.attempt import AttemptStatus

#: Every scene the application registers, with the kwargs its `on_enter` requires.
#: Kept as data so a scene added without a smoke test fails the count assertion.
SCENE_NAMES = [
    "main_menu", "profile_select", "lesson_select", "mode_select",
    "lesson", "results", "leaderboard", "teacher_dashboard", "settings",
]


@pytest.fixture
def ready(app_ctx, display, attempt_factory):
    """A context with one profile, one completed attempt, and an active profile —
    enough state for every scene to have something real to draw."""
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    attempt = attempt_factory(student.id, accuracy=95.0, wpm_net=20.0)
    app_ctx.progression.score(attempt, student)
    return app_ctx, student, attempt


def enter_kwargs(ctx, attempt):
    lesson = ctx.lessons.first_lesson()
    return {
        "mode_select": {"lesson": lesson},
        "lesson": {"lesson": lesson, "mode_key": "lock_on_error"},
        "results": {"attempt": attempt, "lesson": lesson},
    }


# --------------------------------------------------------------------- registry

def test_the_application_registers_exactly_the_documented_scenes(app_ctx, display):
    states = build_state_manager(app_ctx)
    assert sorted(states.registry) == sorted(SCENE_NAMES)


def test_the_game_starts_on_the_main_menu(app_ctx, display, monkeypatch):
    """FR-001."""
    from typecraft.core.game import Game

    monkeypatch.setattr(pygame.display, "set_mode", lambda *a, **k: display)
    game = Game()
    try:
        assert type(game.states.current).__name__ == "MainMenuScene"
        assert game.running is True
    finally:
        game.ctx.db.close()


def test_the_game_loop_runs_frames_and_exits_on_quit(app_ctx, display, monkeypatch):
    """FR-006: a full event/update/render cycle, then a clean stop."""
    from typecraft.core.game import Game

    monkeypatch.setattr(pygame.display, "set_mode", lambda *a, **k: display)
    game = Game()
    try:
        for _ in range(3):
            game._process_events()
            game._update(1 / 30)
            game._render()
        assert game.running is True

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        game._process_events()
        assert game.running is False
    finally:
        game.ctx.db.close()


def test_an_unknown_scene_name_raises(app_ctx, display):
    states = build_state_manager(app_ctx)
    with pytest.raises(ValueError, match="No scene registered"):
        states.change("does_not_exist")


# --------------------------------------------------------------------- every scene

@pytest.mark.parametrize("name", SCENE_NAMES)
def test_every_scene_enters_updates_and_renders(ready, display, name):
    """The blunt instrument that would have caught a crash on entry."""
    ctx, _student, attempt = ready
    kwargs = enter_kwargs(ctx, attempt).get(name, {})

    ctx.states.change(name, **kwargs)

    for _ in range(3):
        ctx.states.update(1 / 30)
        ctx.states.render(display)

    assert isinstance(ctx.states.current, ctx.states.registry[name])


@pytest.mark.parametrize("name", SCENE_NAMES)
def test_every_scene_survives_stray_input(ready, display, name):
    """A child leans on the keyboard and clicks in the dead space. Nothing should
    raise, whichever screen is open."""
    ctx, _student, attempt = ready
    ctx.states.change(name, **enter_kwargs(ctx, attempt).get(name, {}))

    events = [
        pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 5), rel=(1, 1), buttons=(0, 0, 0)),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(640, 700)),
        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(1, 1)),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, unicode=""),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, unicode="\t"),
        pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False, precise_x=0.0,
                           precise_y=-1.0),
    ]
    for event in events:
        ctx.states.handle_event(event)
        ctx.states.update(1 / 30)
    ctx.states.render(display)


@pytest.mark.parametrize("name", SCENE_NAMES)
def test_every_scene_accepts_a_quit_request(ready, display, name):
    """FR-071: `Game` calls this on every scene, so none may raise."""
    ctx, _student, attempt = ready
    ctx.states.change(name, **enter_kwargs(ctx, attempt).get(name, {}))
    ctx.states.notify_quit()


@pytest.mark.parametrize("name", SCENE_NAMES)
def test_every_scene_renders_with_an_empty_database(app_ctx, display, name):
    """First launch on a brand-new school PC: no profiles, no attempts, no PIN.
    Scenes that need a profile are skipped, since the UI cannot reach them."""
    if name in ("lesson_select", "mode_select", "lesson", "results"):
        pytest.skip("unreachable without an active profile")

    build_state_manager(app_ctx)
    app_ctx.states.change(name)
    app_ctx.states.update(1 / 30)
    app_ctx.states.render(display)


# --------------------------------------------------------------------- scene lifecycle

def test_changing_scene_calls_on_exit_then_builds_a_fresh_instance(ready, display):
    """ADR-010: scenes are re-instantiated, so no state leaks between visits."""
    ctx, _student, _attempt = ready
    ctx.states.change("settings")
    first = ctx.states.current

    exits = []
    first.on_exit = lambda: exits.append(True)

    ctx.states.change("settings")

    assert exits == [True]
    assert ctx.states.current is not first


def test_a_lesson_scene_starts_clean_on_re_entry(ready, display):
    """A retry must not inherit the previous attempt's keystrokes."""
    ctx, _student, _attempt = ready
    lesson = ctx.lessons.first_lesson()

    ctx.states.change("lesson", lesson=lesson, mode_key="free_advance")
    target = ctx.states.current.engine.target
    for ch in target[:3]:
        ctx.states.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    assert ctx.states.current.engine.total_keystrokes == 3

    ctx.states.change("lesson", lesson=lesson, mode_key="free_advance")
    assert ctx.states.current.engine.total_keystrokes == 0
    assert ctx.states.current.engine.cursor == 0


def test_an_incomplete_attempt_from_a_scene_change_is_recorded_once(ready, display):
    """Leaving a lesson by any route writes exactly one row (FR-070)."""
    ctx, student, _attempt = ready
    before = ctx.db.query(
        "SELECT COUNT(*) AS c FROM lesson_attempts WHERE status='incomplete'")[0]["c"]

    ctx.states.change("lesson", lesson=ctx.lessons.first_lesson(), mode_key="free_advance")
    scene = ctx.states.current
    target = scene.engine.target
    for ch in target[:4]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))

    after = ctx.db.query(
        "SELECT COUNT(*) AS c FROM lesson_attempts WHERE status='incomplete'")[0]["c"]
    assert after == before + 1


# --------------------------------------------------------------------- degraded environment

def test_the_application_starts_with_no_audio_device(app_ctx, display):
    """AS-03: audio is optional. A school PC with a broken driver must still run —
    the dummy SDL audio driver in conftest is that machine."""
    assert app_ctx.audio is not None
    app_ctx.audio.play("nope.wav")        # must be a silent no-op, not a crash


def test_a_missing_asset_does_not_stop_a_scene_rendering(ready, display):
    """`assets/` is still empty (TC-017), so every scene must already be drawing
    without images. This asserts that rather than assuming it."""
    ctx, _student, attempt = ready
    for name in SCENE_NAMES:
        ctx.states.change(name, **enter_kwargs(ctx, attempt).get(name, {}))
        ctx.states.render(display)
