"""The journey a student actually takes (FR-003, FR-004, AC-02).

Every step is driven by synthesised clicks and key presses through
`handle_event`, not by calling scene methods directly — so this exercises the
button geometry and the event dispatch a child depends on, not just the
transitions. If a button moves outside its scene's hit-testing, this file fails.

Main Menu -> Profile Select -> Lesson Select -> Mode Select -> Lesson -> Results
"""

import pygame
import pytest

from typecraft.core.game import build_state_manager


def click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pygame.Rect(rect).center)


def press(key, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def type_char(ch):
    return pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch)


def scene_name(ctx):
    return type(ctx.states.current).__name__


@pytest.fixture
def app(app_ctx, display):
    build_state_manager(app_ctx)
    app_ctx.states.change("main_menu")
    return app_ctx


def create_profile(app, name="Amina"):
    """Drive the Create Profile flow the way a teacher would."""
    scene = app.states.current
    scene.name_input.focused = True
    for ch in name:
        scene.handle_event(type_char(ch))
    scene.handle_event(click(scene.create_button.rect))
    return app.profiles.list_all()[-1]


# --------------------------------------------------------------------- main menu

@pytest.mark.parametrize("index,expected", [
    (0, "ProfileSelectScene"),
    (1, "LeaderboardScene"),
    (2, "SettingsScene"),
    (3, "TeacherDashboardScene"),
])
def test_every_main_menu_button_reaches_its_screen(app, index, expected):
    """FR-001/FR-003, clicked rather than called."""
    scene = app.states.current
    scene.handle_event(click(scene.widgets[index].rect))
    assert scene_name(app) == expected


@pytest.mark.parametrize("destination", ["leaderboard", "settings", "teacher_dashboard"])
def test_back_returns_to_the_main_menu(app, destination):
    """FR-004: no screen is a dead end."""
    app.states.change(destination)
    scene = app.states.current
    scene.handle_event(click(scene.back_button.rect))
    assert scene_name(app) == "MainMenuScene"


# --------------------------------------------------------------------- the full journey

def test_a_student_can_walk_from_the_menu_to_a_finished_lesson(app, display):
    """The whole product in one test: menu, profile, lesson, mode, typing, results —
    and the attempt on record at the end."""
    menu = app.states.current
    menu.handle_event(click(menu.widgets[0].rect))
    assert scene_name(app) == "ProfileSelectScene"

    student = create_profile(app)
    assert student.name == "Amina"

    # Pick that profile from the grid.
    select = app.states.current
    _profile, card = select.profile_buttons[0]
    select.handle_event(click(select.panel.screen_rect(card)))
    assert scene_name(app) == "LessonSelectScene"
    assert app.active_profile.id == student.id

    # Only lesson 1 is unlocked, so it is the only clickable card (FR-027).
    lessons = app.states.current
    unlocked = [(l, r) for l, is_unlocked, _s, r in lessons.cards if is_unlocked]
    assert len(unlocked) == 1
    lessons.handle_event(click(lessons.panel.screen_rect(unlocked[0][1])))
    assert scene_name(app) == "ModeSelectScene"

    # Choose a mode.
    modes = app.states.current
    assert len(modes.mode_buttons) == 3
    modes.handle_event(click(modes.mode_buttons[0].rect))
    assert scene_name(app) == "LessonScene"

    # Type the whole drill correctly.
    lesson_scene = app.states.current
    target = lesson_scene.engine.target
    for ch in target:
        if scene_name(app) != "LessonScene":
            break
        app.states.handle_event(type_char(ch))

    assert scene_name(app) == "ResultsScene", "finishing the text must reach Results"

    attempt = app.states.current.attempt
    assert attempt.status.value == "complete"
    assert attempt.accuracy == pytest.approx(100.0)
    assert attempt.stars == 3

    rows = app.db.query("SELECT * FROM lesson_attempts WHERE profile_id=?", (student.id,))
    assert len(rows) == 1 and rows[0]["status"] == "complete"
    app.states.render(display)


def test_finishing_a_lesson_unlocks_the_next_one_in_the_grid(app, display):
    """FR-061 seen from the UI: the next card becomes clickable."""
    app.states.change("profile_select")
    student = create_profile(app)
    app.active_profile = student

    app.states.change("lesson", lesson=app.lessons.first_lesson(), mode_key="free_advance")
    scene = app.states.current
    for ch in scene.engine.target:
        if scene_name(app) != "LessonScene":
            break
        app.states.handle_event(type_char(ch))
    assert scene_name(app) == "ResultsScene"

    app.states.change("lesson_select")
    unlocked = [l.id for l, is_unlocked, _s, _r in app.states.current.cards if is_unlocked]
    assert len(unlocked) == 2, f"expected lessons 1 and 2 unlocked, got {unlocked}"


# --------------------------------------------------------------------- results screen

@pytest.fixture
def at_results(app, attempt_factory):
    student = app.profiles.create("Amina", "avatar_fox")
    app.active_profile = student
    lesson = app.lessons.first_lesson()
    attempt = attempt_factory(student.id, accuracy=95.0)
    app.progression.score(attempt, student)
    app.states.change("results", attempt=attempt, lesson=lesson)
    return app


@pytest.mark.parametrize("index,expected", [
    (0, "ModeSelectScene"),      # Retry
    (1, "LessonSelectScene"),    # Continue
    (2, "LeaderboardScene"),     # Leaderboard
])
def test_every_results_button_reaches_its_screen(at_results, index, expected):
    """FR-003."""
    scene = at_results.states.current
    scene.handle_event(click(scene.buttons[index].rect))
    assert scene_name(at_results) == expected


def test_retry_returns_to_the_same_lesson(at_results):
    scene = at_results.states.current
    lesson_id = scene.lesson.id
    scene.handle_event(click(scene.buttons[0].rect))
    assert at_results.states.current.lesson.id == lesson_id


# --------------------------------------------------------------------- navigation back

def test_mode_select_can_go_back_to_the_lesson_grid(app):
    app.states.change("profile_select")
    student = create_profile(app)
    app.active_profile = student

    app.states.change("mode_select", lesson=app.lessons.first_lesson())
    scene = app.states.current
    scene.handle_event(click(scene.back_button.rect))
    assert scene_name(app) == "LessonSelectScene"


def test_lesson_select_can_switch_profile(app):
    app.states.change("profile_select")
    student = create_profile(app)
    app.active_profile = student

    app.states.change("lesson_select")
    scene = app.states.current
    scene.handle_event(click(scene.back_button.rect))
    assert scene_name(app) == "ProfileSelectScene"


def test_escaping_a_lesson_returns_to_the_grid(app):
    app.states.change("profile_select")
    student = create_profile(app)
    app.active_profile = student

    app.states.change("lesson", lesson=app.lessons.first_lesson(), mode_key="lock_on_error")
    app.states.handle_event(press(pygame.K_ESCAPE))
    assert scene_name(app) == "LessonSelectScene"


# --------------------------------------------------------------------- profile creation

def test_a_blank_profile_name_is_rejected(app):
    """FR-016: whitespace must not create a row."""
    app.states.change("profile_select")
    scene = app.states.current
    scene.name_input.focused = True
    for ch in "   ":
        scene.handle_event(type_char(ch))
    scene.handle_event(click(scene.create_button.rect))

    assert app.profiles.list_all() == []


def test_a_created_profile_appears_in_the_grid_immediately(app):
    app.states.change("profile_select")
    scene = app.states.current
    assert scene.profile_buttons == []

    create_profile(app, "Bilal")

    assert len(app.states.current.profile_buttons) == 1
    assert app.states.current.profile_buttons[0][0].name == "Bilal"


def test_a_new_profile_can_only_start_lesson_one(app):
    """FR-015/FR-027 through the UI: 19 locked cards reject clicks."""
    app.states.change("profile_select")
    student = create_profile(app)
    app.active_profile = student
    app.states.change("lesson_select")
    scene = app.states.current

    for lesson, is_unlocked, _stars, rect in scene.cards:
        if is_unlocked:
            continue
        scene.panel.scroll_to(0)
        scene.handle_event(click(scene.panel.screen_rect(rect)))
        assert scene_name(app) == "LessonSelectScene", f"{lesson.id} was startable while locked"


# --------------------------------------------------------------------- settings & dashboard

def test_settings_changes_survive_leaving_and_returning(app):
    """FR-131/FR-132 through the UI rather than the manager."""
    app.states.change("settings")
    scene = app.states.current
    scene.handle_event(click(scene.vol_down.rect))
    lowered = scene.volume_bar.value

    scene.handle_event(click(scene.back_button.rect))
    app.states.change("settings")

    assert app.states.current.volume_bar.value == pytest.approx(lowered)


def test_the_dashboard_pin_gate_is_driven_from_the_keyboard(app):
    """FR-121: typing the PIN and pressing Return, as a teacher would."""
    app.config.set_pin("2468")
    app.states.change("teacher_dashboard")
    scene = app.states.current
    assert scene.authenticated is False

    scene.pin_input.focused = True
    for ch in "2468":
        scene.handle_event(type_char(ch))
    scene.handle_event(press(pygame.K_RETURN))

    assert scene.authenticated is True


def test_a_wrong_pin_typed_at_the_dashboard_is_refused(app):
    app.config.set_pin("2468")
    app.states.change("teacher_dashboard")
    scene = app.states.current

    scene.pin_input.focused = True
    for ch in "1111":
        scene.handle_event(type_char(ch))
    scene.handle_event(press(pygame.K_RETURN))

    assert scene.authenticated is False
    assert scene.error == "Incorrect PIN"
