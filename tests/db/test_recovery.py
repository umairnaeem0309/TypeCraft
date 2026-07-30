"""Power-loss recovery for an in-flight attempt (FR-073, FR-074, FR-075, ADR-004).

The scenario this exists for: a child is halfway through a lesson and the school
loses power. On the next launch their attempt must be a recoverable, correctly
classified record — never a lost one, and never two rows for one attempt.
"""

import pytest

from typecraft.engine.input_modes import create_mode
from typecraft.engine.typing_engine import TypingEngine
from typecraft.managers.database import Database
from typecraft.models.attempt import AttemptStatus


def make_engine(profile_id, target="asdf jkl asdf", mode_key="lock_on_error"):
    return TypingEngine(target=target, mode=create_mode(mode_key), profile_id=profile_id,
                        lesson_id="t1l1", mode_key=mode_key, tier=1)


def rows(ctx):
    return ctx.db.query("SELECT * FROM lesson_attempts ORDER BY id")


def test_a_checkpoint_reserves_one_in_progress_row(profile):
    ctx, student = profile
    engine = make_engine(student.id)
    for ch in "asdf":
        engine.feed_key(ch)

    row_id = ctx.progression.checkpoint(engine)

    all_rows = rows(ctx)
    assert len(all_rows) == 1
    assert all_rows[0]["id"] == row_id
    assert all_rows[0]["status"] == "in_progress"
    assert all_rows[0]["total_keystrokes"] == 4
    assert all_rows[0]["completed_at"] in ("", None)


def test_repeated_checkpoints_update_the_same_row(profile):
    """ADR-004: one row per attempt, however long the lesson runs."""
    ctx, student = profile
    engine = make_engine(student.id)

    row_id = None
    for ch in "asdf jkl":
        engine.feed_key(ch)
        row_id = ctx.progression.checkpoint(engine, row_id)

    all_rows = rows(ctx)
    assert len(all_rows) == 1, "each checkpoint inserted a new row"
    assert all_rows[0]["total_keystrokes"] == 8


def test_a_checkpointed_attempt_awards_nothing_while_in_flight(profile):
    """FR-075: an in_progress row must not touch XP, streaks, badges or unlocks."""
    ctx, student = profile
    engine = make_engine(student.id)
    for ch in "asdf":
        engine.feed_key(ch)
    ctx.progression.checkpoint(engine)

    assert ctx.db.query("SELECT total_xp FROM profiles WHERE id=?",
                        (student.id,))[0]["total_xp"] == 0
    assert ctx.db.query("SELECT COUNT(*) AS c FROM profile_badges")[0]["c"] == 0
    assert ctx.lessons.is_unlocked(student, "t1l2") is False


def test_completing_promotes_the_checkpointed_row_instead_of_adding_one(profile):
    """The bug ADR-004 prevents: without promotion, a checkpointed attempt that
    then completes would leave both an in_progress and a complete row, and every
    average would count the lesson twice."""
    ctx, student = profile
    target = "asdf"
    engine = make_engine(student.id, target)

    engine.feed_key("a")
    row_id = ctx.progression.checkpoint(engine)
    for ch in target[1:]:
        engine.feed_key(ch)

    scored = ctx.progression.score(
        engine.result(status=AttemptStatus.COMPLETE), student, row_id)

    all_rows = rows(ctx)
    assert len(all_rows) == 1
    assert all_rows[0]["id"] == row_id
    assert all_rows[0]["status"] == "complete"
    assert all_rows[0]["accuracy"] == pytest.approx(100.0)
    assert all_rows[0]["xp_awarded"] == scored.xp_awarded > 0
    assert all_rows[0]["completed_at"] != ""


def test_abandoning_promotes_the_checkpointed_row_to_incomplete(profile):
    ctx, student = profile
    engine = make_engine(student.id)
    for ch in "asd":
        engine.feed_key(ch)
    row_id = ctx.progression.checkpoint(engine)

    ctx.progression.score(engine.result(status=AttemptStatus.INCOMPLETE), student, row_id)

    all_rows = rows(ctx)
    assert len(all_rows) == 1
    assert all_rows[0]["status"] == "incomplete"
    assert all_rows[0]["xp_awarded"] == 0


def test_a_simulated_power_cut_recovers_as_one_incomplete_attempt(profile, writable_dir):
    """FR-073 + FR-074 end to end: checkpoint, lose the process without ever
    scoring, reopen. Exactly one row, reclassified to incomplete."""
    ctx, student = profile
    engine = make_engine(student.id)
    for ch in "asdf jkl":
        engine.feed_key(ch)
    ctx.progression.checkpoint(engine)
    ctx.db.close()                      # the power cut: no score(), no clean shutdown

    reopened = Database()
    try:
        recovered = reopened.query("SELECT * FROM lesson_attempts")
        assert len(recovered) == 1
        assert recovered[0]["status"] == "incomplete"
        assert recovered[0]["total_keystrokes"] == 8, "the work done is still on record"
        # And it stays out of every aggregate (FR-075).
        assert reopened.query(
            "SELECT COUNT(*) AS c FROM lesson_attempts WHERE status='complete'"
        )[0]["c"] == 0
    finally:
        reopened.close()


def test_recovery_leaves_a_previously_completed_attempt_alone(profile, writable_dir):
    """A crash must not rewrite history the student already earned."""
    ctx, student = profile
    ctx.progression.score(
        make_engine(student.id, "as").result(status=AttemptStatus.COMPLETE), student)

    engine = make_engine(student.id)
    engine.feed_key("a")
    ctx.progression.checkpoint(engine)
    ctx.db.close()

    reopened = Database()
    try:
        counts = {r["status"]: r["c"] for r in reopened.query(
            "SELECT status, COUNT(*) AS c FROM lesson_attempts GROUP BY status")}
        assert counts == {"complete": 1, "incomplete": 1}
    finally:
        reopened.close()


def test_no_database_write_happens_on_the_keystroke_path(profile):
    """NFR-007/FR-073. 100 keystrokes must cost zero queries — checkpointing is
    driven from update(dt), not from feed_key()."""
    ctx, student = profile
    engine = make_engine(student.id, "a" * 200)

    calls = []
    original = ctx.db.execute
    ctx.db.execute = lambda *a, **k: (calls.append(a), original(*a, **k))[1]

    for _ in range(100):
        engine.feed_key("a")

    assert calls == [], f"{len(calls)} database writes on the keystroke path"


# --------------------------------------------------------------------- scene timing

def test_the_lesson_scene_checkpoints_on_a_timer_not_per_keystroke(app_ctx, display):
    """FR-073: the interval is time-based, so a fast typist and a slow one produce
    the same number of writes per minute."""
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Timed", "avatar_owl")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="free_advance")

    # No keystrokes yet: nothing to checkpoint, however much time passes.
    scene.update(60.0)
    assert rows(app_ctx) == []

    scene.engine.feed_key(lesson.target_text()[0])

    # Below the interval: still nothing written.
    scene.update(app_ctx.progression.CHECKPOINT_INTERVAL_SEC / 2)
    assert rows(app_ctx) == []

    # Crossing the interval writes exactly one row...
    scene.update(app_ctx.progression.CHECKPOINT_INTERVAL_SEC)
    first = rows(app_ctx)
    assert len(first) == 1 and first[0]["status"] == "in_progress"

    # ...and crossing it again updates that row rather than adding another.
    scene.update(app_ctx.progression.CHECKPOINT_INTERVAL_SEC)
    assert len(rows(app_ctx)) == 1
