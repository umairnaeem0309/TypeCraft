"""Teacher dashboard: per-student statistics, PIN gate, confirmed atomic reset
(FR-120..FR-127).

Before TC-013 the dashboard showed name, level and streak only — no averages, no
lessons-completed, no XP, no badge count — and "Reset Progress" wrote immediately
on a single click, next to every other student's identical button.
"""

import pygame
import pytest

from typecraft.models.attempt import AttemptStatus
from typecraft.scenes.teacher_dashboard import TeacherDashboardScene


def click(button):
    """Synthesise the click a teacher would make."""
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center)


@pytest.fixture
def dashboard(app_ctx, display):
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    return app_ctx, scene


# --------------------------------------------------------------------- statistics

def test_summary_reports_every_required_field(profile, attempt_factory):
    """FR-122."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=90.0, wpm_net=20.0), student)

    summary = ctx.progression.student_summary(student.id)

    for field in ("name", "level", "total_xp", "avg_wpm_net", "avg_accuracy",
                  "lessons_completed", "badge_count", "current_streak", "longest_streak"):
        assert field in summary, field
    assert summary["name"] == "Test Student"


def test_averages_are_over_completed_attempts_only(profile, attempt_factory):
    """FR-123. A child who abandons four attempts at 10 % and finishes one at 90 %
    has averaged 90 %, and a teacher acting on 26 % would be misled."""
    ctx, student = profile
    for _ in range(4):
        ctx.progression.score(
            attempt_factory(student.id, accuracy=10.0, wpm_net=2.0,
                            status=AttemptStatus.INCOMPLETE), student)
    ctx.progression.score(attempt_factory(student.id, accuracy=90.0, wpm_net=20.0), student)

    summary = ctx.progression.student_summary(student.id)
    assert summary["avg_accuracy"] == pytest.approx(90.0)
    assert summary["avg_wpm_net"] == pytest.approx(20.0)
    assert summary["completed_attempts"] == 1


def test_averages_are_none_when_nothing_is_finished(profile):
    """FR-123: the UI must be able to say "nothing yet" rather than print 0 %,
    which would read as "tried and failed"."""
    ctx, student = profile
    summary = ctx.progression.student_summary(student.id)

    assert summary["avg_wpm_net"] is None
    assert summary["avg_accuracy"] is None
    assert summary["lessons_completed"] == 0


def test_averages_are_the_mean_of_all_completed_attempts(profile, attempt_factory):
    ctx, student = profile
    for accuracy, wpm in ((90.0, 10.0), (100.0, 30.0)):
        ctx.progression.score(
            attempt_factory(student.id, accuracy=accuracy, wpm_net=wpm), student)

    summary = ctx.progression.student_summary(student.id)
    assert summary["avg_accuracy"] == pytest.approx(95.0)
    assert summary["avg_wpm_net"] == pytest.approx(20.0)


def test_lessons_completed_counts_distinct_lessons(profile, attempt_factory):
    """Replaying lesson 1 twenty times is one lesson learned, not twenty."""
    ctx, student = profile
    for _ in range(20):
        ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=95.0), student)
    ctx.progression.score(attempt_factory(student.id, "t1l2", accuracy=95.0), student)

    summary = ctx.progression.student_summary(student.id)
    assert summary["lessons_completed"] == 2
    assert summary["completed_attempts"] == 21


def test_badge_and_streak_figures_are_reported(profile, attempt_factory):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=100.0), student)

    summary = ctx.progression.student_summary(student.id)
    assert summary["badge_count"] >= 2        # first_steps + sharp_shooter
    assert summary["current_streak"] == 1
    assert summary["longest_streak"] == 1
    assert summary["total_xp"] > 0


def test_class_summary_lists_every_student_by_name(app_ctx, attempt_factory):
    for name in ("Zainab", "Amina", "Bilal"):
        app_ctx.profiles.create(name, "avatar_fox")

    rows = app_ctx.progression.class_summary()

    assert [r["name"] for r in rows] == ["Amina", "Bilal", "Zainab"]


def test_a_student_who_never_played_still_appears(app_ctx):
    """Unlike the leaderboard, the register must show everyone — a teacher needs to
    see who has not started."""
    app_ctx.profiles.create("Never Typed", "avatar_owl")

    rows = app_ctx.progression.class_summary()
    assert len(rows) == 1
    assert rows[0]["lessons_completed"] == 0
    assert rows[0]["avg_accuracy"] is None


def test_summary_for_an_unknown_profile_raises(app_ctx):
    with pytest.raises(ValueError):
        app_ctx.progression.student_summary(9999)


# --------------------------------------------------------------------- PIN gate

def test_the_dashboard_opens_when_no_pin_is_configured(dashboard):
    """FR-120: a school that has not set a PIN must not be locked out of its own
    dashboard."""
    ctx, scene = dashboard
    assert ctx.config.has_pin() is False
    assert scene.authenticated is True


def test_a_configured_pin_gates_the_dashboard(app_ctx, display):
    """FR-120/FR-121."""
    app_ctx.config.set_pin("2468")
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()

    assert scene.authenticated is False

    scene.pin_input.text = "1357"
    scene._try_pin()
    assert scene.authenticated is False
    assert scene.error == "Incorrect PIN"
    assert scene.pin_input.text == "", "the field must be cleared after a failed attempt"

    scene.pin_input.text = "2468"
    scene._try_pin()
    assert scene.authenticated is True
    assert scene.error == ""


def test_reset_buttons_are_unreachable_before_authentication(app_ctx, display, attempt_factory):
    """FR-124: the gate has to cover the destructive action, not just the view."""
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    app_ctx.config.set_pin("2468")

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    assert scene.authenticated is False

    for _summary, btn in scene.reset_buttons:
        scene.handle_event(click(btn))

    assert scene.pending_reset is None
    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1


# --------------------------------------------------------------------- confirmed reset

def test_clicking_reset_only_asks_and_writes_nothing(app_ctx, display, attempt_factory):
    """FR-125 — the defect D-13 regression test. One click next to a row of
    identical buttons must not be able to erase a child's term of work."""
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.handle_event(click(scene.reset_buttons[0][1]))

    assert scene.pending_reset is not None
    assert scene.pending_reset["name"] == "Amina"
    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1
    assert app_ctx.db.query(
        "SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"] > 0


def test_cancelling_leaves_everything_untouched(app_ctx, display, attempt_factory):
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    before = app_ctx.db.query("SELECT * FROM profiles WHERE id=?", (student.id,))[0]

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.handle_event(click(scene.cancel_button))

    assert scene.pending_reset is None
    assert app_ctx.db.query("SELECT * FROM profiles WHERE id=?", (student.id,))[0] == before
    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1


def test_escape_cancels_the_confirmation(app_ctx, display, attempt_factory):
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))

    assert scene.pending_reset is None
    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1


def test_confirming_resets_that_student_only(app_ctx, display, attempt_factory):
    """FR-126/FR-127: the right child, all of it, and nobody else."""
    amina = app_ctx.profiles.create("Amina", "avatar_fox")
    bilal = app_ctx.profiles.create("Bilal", "avatar_owl")
    for student in (amina, bilal):
        app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    row = next(r for r in scene.reset_buttons if r[0]["name"] == "Amina")
    scene.handle_event(click(row[1]))
    scene.handle_event(click(scene.confirm_button))

    assert scene.pending_reset is None
    reset = app_ctx.progression.student_summary(amina.id)
    kept = app_ctx.progression.student_summary(bilal.id)

    assert (reset["total_xp"], reset["level"], reset["lessons_completed"]) == (0, 1, 0)
    assert reset["badge_count"] == 0
    assert reset["name"] == "Amina", "the child's profile must survive (FR-127)"
    assert kept["total_xp"] > 0, "the other student must be untouched"
    assert kept["lessons_completed"] == 1


def test_a_reset_student_starts_again_at_lesson_one(app_ctx, display, attempt_factory):
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    assert app_ctx.lessons.is_unlocked(student, "t1l2") is True

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.handle_event(click(scene.confirm_button))

    fresh = app_ctx.profiles.load(student.id)
    assert app_ctx.lessons.is_unlocked(fresh, app_ctx.lessons.first_lesson().id) is True
    assert app_ctx.lessons.is_unlocked(fresh, "t1l2") is False


def test_the_table_refreshes_after_a_reset(app_ctx, display, attempt_factory):
    """The teacher must see the zeroes, not the stale figures they just erased."""
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    assert scene.summaries[0]["total_xp"] > 0

    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.handle_event(click(scene.confirm_button))

    assert scene.summaries[0]["total_xp"] == 0
    assert scene.summaries[0]["avg_accuracy"] is None


def test_confirming_with_nothing_pending_is_a_no_op(app_ctx, display, attempt_factory):
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene._confirm_reset()

    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1


def test_resetting_the_active_profile_updates_the_live_object(app_ctx, display, attempt_factory):
    """If the child is mid-session, the in-memory Profile must not keep the XP the
    reset just cleared — a later save() would write it back."""
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.handle_event(click(scene.confirm_button))

    assert app_ctx.active_profile.total_xp == 0
    assert app_ctx.active_profile.level == 1


# --------------------------------------------------------------------- rendering

def test_the_dashboard_renders_with_students_and_without(app_ctx, display, attempt_factory):
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.render(display)             # empty class

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    scene.on_enter()
    scene.render(display)             # one student with figures

    scene.handle_event(click(scene.reset_buttons[0][1]))
    scene.render(display)             # confirmation panel over the table


def test_the_pin_screen_renders_its_error(app_ctx, display):
    app_ctx.config.set_pin("2468")
    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.pin_input.text = "0000"
    scene._try_pin()
    scene.render(display)
