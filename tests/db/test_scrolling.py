"""Classroom-scale scrolling (FR-014, FR-026, FR-124, PR-004).

Three screens laid content out past the bottom of the 1280x720 window and let it
fall off: Profile Select from the 9th child, Lesson Select's fourth row of cards,
and the dashboard for any class over about twelve. Nothing errored — the students
and lessons were simply not there.

The bounds tests below are the real contract: for a realistic class, every item a
teacher can see must be inside the window, and every item must be *reachable* by
scrolling.
"""

import pygame
import pytest

from typecraft.ui import theme
from typecraft.ui.scroll_panel import ScrollPanel

WINDOW = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
CLASS_SIZE = 40          # AS-05: the assumed classroom ceiling


# --------------------------------------------------------------------- panel mechanics

def test_a_panel_with_short_content_does_not_scroll():
    panel = ScrollPanel(pygame.Rect(0, 100, 800, 400), content_height=200)
    assert panel.scrollable is False
    assert panel.max_offset == 0

    panel.scroll_by(500)
    assert panel.offset == 0, "nothing to scroll, so the view must not move"


def test_scrolling_is_clamped_at_both_ends():
    panel = ScrollPanel(pygame.Rect(0, 0, 800, 400), content_height=1000)
    assert panel.max_offset == 600

    panel.scroll_by(-100)
    assert panel.offset == 0

    panel.scroll_by(10_000)
    assert panel.offset == 600, "must stop at the end, not scroll into empty space"


def test_content_space_is_relative_to_the_viewport_top():
    """A scene lays its first row out at y = 0 and never needs to know where the
    viewport sits — the panel maps content to screen."""
    panel = ScrollPanel(pygame.Rect(0, 150, 800, 300), content_height=900)

    assert panel.screen_rect(pygame.Rect(10, 0, 100, 40)).y == 150
    panel.scroll_to(50)
    assert panel.screen_rect(pygame.Rect(10, 0, 100, 40)).y == 100


def test_screen_and_content_translation_are_exact_inverses():
    """If these ever disagree, a click lands on the row above or below the one the
    teacher is looking at."""
    panel = ScrollPanel(pygame.Rect(0, 150, 800, 300), content_height=2000)
    for offset in (0, 37, 500, panel.max_offset):
        panel.scroll_to(offset)
        for content_y in (0, 44, 811):
            rect = pygame.Rect(5, content_y, 100, 30)
            screen = panel.screen_rect(rect)
            assert panel.content_pos((screen.x, screen.y)) == (rect.x, rect.y)


def test_shrinking_the_content_pulls_the_view_back_into_range():
    """Resetting the last student must not leave the view stranded past the end."""
    panel = ScrollPanel(pygame.Rect(0, 0, 800, 400), content_height=2000)
    panel.scroll_to(panel.max_offset)
    assert panel.offset == 1600

    panel.set_content_height(500)
    assert panel.offset == 100 == panel.max_offset


def test_a_click_outside_the_viewport_is_rejected_not_translated():
    """The important half of `translated`. Without it, a click just below the panel
    would be shifted into a child's row and select the wrong student."""
    panel = ScrollPanel(pygame.Rect(0, 100, 800, 200), content_height=1000)

    inside = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 150))
    assert panel.translated(inside).pos == (400, 50)

    below = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 400))
    assert panel.translated(below) is None


def test_page_and_home_end_keys_scroll(display):
    panel = ScrollPanel(pygame.Rect(0, 0, 800, 300), content_height=1500)

    assert panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN)) is True
    assert panel.offset == 300

    panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
    assert panel.offset == panel.max_offset

    panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME))
    assert panel.offset == 0


def test_a_non_scrolling_panel_consumes_no_input():
    """Otherwise a panel with three students in it would swallow key presses the
    rest of the screen needs."""
    panel = ScrollPanel(pygame.Rect(0, 0, 800, 400), content_height=100)
    assert panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN)) is False


# --------------------------------------------------------------------- profile select

def make_class(ctx, size=CLASS_SIZE):
    for i in range(size):
        ctx.profiles.create(f"Student {i:02d}", "avatar_fox")


def test_every_visible_profile_card_is_inside_the_window(app_ctx, display):
    """FR-014 — the defect D-18 regression test."""
    from typecraft.scenes.profile_select import ProfileSelectScene

    make_class(app_ctx)
    scene = ProfileSelectScene(app_ctx)
    scene.on_enter()

    for offset in (0, scene.panel.max_offset // 2, scene.panel.max_offset):
        scene.panel.scroll_to(offset)
        for _profile, content_rect in scene.profile_buttons:
            if not scene.panel.is_visible(content_rect):
                continue
            visible = scene.panel.screen_rect(content_rect).clip(scene.panel.rect)
            assert WINDOW.contains(visible), f"card outside the window at offset {offset}"


def test_every_profile_is_reachable_by_scrolling(app_ctx, display):
    from typecraft.scenes.profile_select import ProfileSelectScene

    make_class(app_ctx)
    scene = ProfileSelectScene(app_ctx)
    scene.on_enter()

    seen = set()
    for offset in range(0, scene.panel.max_offset + 1, 20):
        scene.panel.scroll_to(offset)
        seen |= {p.id for p, r in scene.profile_buttons if scene.panel.is_visible(r)}
    scene.panel.scroll_to(scene.panel.max_offset)
    seen |= {p.id for p, r in scene.profile_buttons if scene.panel.is_visible(r)}

    assert len(seen) == CLASS_SIZE, f"{CLASS_SIZE - len(seen)} students unreachable"


def test_a_scrolled_click_selects_the_card_under_the_cursor(app_ctx, display):
    """The bug a scrolling refactor invites: hit-testing against stale positions."""
    from typecraft.scenes.profile_select import ProfileSelectScene

    make_class(app_ctx)
    scene = ProfileSelectScene(app_ctx)
    scene.on_enter()
    scene.panel.scroll_to(scene.panel.max_offset)

    # A card straddling the top edge is "visible" but its centre is outside the
    # viewport, so pick one that is fully on screen.
    target, content_rect = next(
        (p, r) for p, r in scene.profile_buttons
        if scene.panel.rect.contains(scene.panel.screen_rect(r)))
    where = scene.panel.screen_rect(content_rect).center

    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=where))

    assert app_ctx.active_profile.id == target.id


def test_a_click_below_the_grid_selects_nobody(app_ctx, display):
    from typecraft.scenes.profile_select import ProfileSelectScene

    make_class(app_ctx)
    scene = ProfileSelectScene(app_ctx)
    scene.on_enter()

    scene.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=(theme.SCREEN_WIDTH // 2, 700)))

    assert app_ctx.active_profile is None


def test_the_profile_grid_renders_at_class_scale(app_ctx, display):
    from typecraft.scenes.profile_select import ProfileSelectScene

    make_class(app_ctx)
    scene = ProfileSelectScene(app_ctx)
    scene.on_enter()
    scene.render(display)
    scene.panel.scroll_to(scene.panel.max_offset)
    scene.render(display)


# --------------------------------------------------------------------- lesson select

def test_every_lesson_card_is_reachable_and_inside_the_window(app_ctx, display):
    """FR-026: the fourth row of cards used to be clipped by the window edge, so the
    last five lessons could not be started."""
    from typecraft.scenes.lesson_select import LessonSelectScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonSelectScene(app_ctx)
    scene.on_enter()

    assert len(scene.cards) >= 20

    seen = set()
    for offset in range(0, scene.panel.max_offset + 1, 20):
        scene.panel.scroll_to(offset)
        for lesson, _unlocked, _stars, rect in scene.cards:
            if scene.panel.is_visible(rect):
                seen.add(lesson.id)
                visible = scene.panel.screen_rect(rect).clip(scene.panel.rect)
                assert WINDOW.contains(visible)
    scene.panel.scroll_to(scene.panel.max_offset)
    seen |= {l.id for l, _u, _s, r in scene.cards if scene.panel.is_visible(r)}

    assert len(seen) == len(scene.cards), "some lessons are unreachable"


def test_a_locked_lesson_still_cannot_be_started_when_scrolled(app_ctx, display):
    """Scrolling must not become a way around the unlock gate."""
    from typecraft.scenes.lesson_select import LessonSelectScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonSelectScene(app_ctx)
    scene.on_enter()
    scene.panel.scroll_to(scene.panel.max_offset)

    locked = [(l, r) for l, unlocked, _s, r in scene.cards
              if not unlocked and scene.panel.rect.contains(scene.panel.screen_rect(r))]
    assert locked, "expected locked lessons at the bottom of the grid"

    before = type(app_ctx.states.current).__name__
    for _lesson, rect in locked:
        scene.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=scene.panel.screen_rect(rect).center))
    assert type(app_ctx.states.current).__name__ == before


# --------------------------------------------------------------------- dashboard

def test_every_dashboard_row_is_reachable_at_class_scale(app_ctx, display):
    """FR-124."""
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    make_class(app_ctx)
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()

    assert len(scene.reset_buttons) == CLASS_SIZE
    assert scene.panel.scrollable, "40 students must not fit without scrolling"

    seen = set()
    for offset in range(0, scene.panel.max_offset + 1, 20):
        scene.panel.scroll_to(offset)
        seen |= {s["name"] for s, b in scene.reset_buttons if scene.panel.is_visible(b.rect)}
    scene.panel.scroll_to(scene.panel.max_offset)
    seen |= {s["name"] for s, b in scene.reset_buttons if scene.panel.is_visible(b.rect)}

    assert len(seen) == CLASS_SIZE


def test_a_scrolled_reset_click_targets_the_visible_student(app_ctx, display):
    """The highest-consequence version of the stale-hit-test bug: resetting the
    wrong child's work."""
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    make_class(app_ctx)
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.panel.scroll_to(scene.panel.max_offset)

    summary, button = next(
        (s, b) for s, b in scene.reset_buttons
        if scene.panel.rect.contains(scene.panel.screen_rect(b.rect)))
    where = scene.panel.screen_rect(button.rect).center

    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=where))

    assert scene.pending_reset is not None
    assert scene.pending_reset["name"] == summary["name"]


def test_the_dashboard_renders_at_class_scale(app_ctx, display):
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    make_class(app_ctx)
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.render(display)
    scene.panel.scroll_to(scene.panel.max_offset)
    scene.render(display)


def test_the_dashboard_still_queries_once_per_entry_not_per_frame(app_ctx, display):
    """PR-004: layout and queries happen on entry. Rendering forty rows sixty times
    a second must not hit the database."""
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    make_class(app_ctx, 10)
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()

    calls = []
    original = app_ctx.db.query
    app_ctx.db.query = lambda *a, **k: (calls.append(a), original(*a, **k))[1]
    try:
        for _ in range(5):
            scene.render(display)
            scene.update(1 / 30)
    finally:
        app_ctx.db.query = original

    assert calls == [], f"{len(calls)} queries during render/update"
