"""Transaction boundaries (DR-010).

Two multi-statement mutations must be all-or-nothing: scoring a completed attempt
(attempt row + progress cache + XP + streak + unlock + badges) and resetting one
student (delete attempts + progress + badges, zero XP/level/streaks, re-unlock
lesson 1). A failure part-way through either one leaves a child's record in a
state no screen can explain — half-wiped progress with intact XP, or the reverse.

`Database.execute()` currently commits after *every* statement, so the enclosing
`begin()` is over before the second statement runs and `rollback()` has nothing
to undo. That is defect D-04, and it is why `TeacherDashboardScene._reset_progress`
is not the atomic operation its `try/except: rollback(); raise` implies.
"""

import sqlite3

import pytest


def _profile_count(db):
    return db.query("SELECT COUNT(*) AS c FROM profiles")[0]["c"]


def test_a_single_statement_is_durable(db):
    """The autocommit path must keep working — most writes are single statements."""
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    assert _profile_count(db) == 1


@pytest.mark.xfail(strict=True, reason="defect D-04: execute() commits every statement, so "
                                      "begin()/rollback() cannot undo anything")
def test_rollback_undoes_every_statement_since_begin(db):
    """The property the teacher's reset depends on."""
    db.begin()
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('B','x','t')")
    db.rollback()

    assert _profile_count(db) == 0


@pytest.mark.xfail(strict=True, reason="defect D-04: the first execute() inside begin() "
                                      "commits, so earlier statements survive the rollback")
def test_a_failure_midway_through_a_reset_changes_nothing(db, profile, attempt_factory):
    """FR-126, and the reason this defect is P0: a reset that fails after deleting
    attempts but before zeroing XP leaves a student with no history and a level
    they can no longer have earned."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id), student)

    before = {
        "attempts": ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"],
        "progress": ctx.db.query("SELECT COUNT(*) AS c FROM lesson_progress")[0]["c"],
        "xp": ctx.db.query("SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"],
    }
    assert before["attempts"] == 1 and before["xp"] > 0, "fixture did not produce a scored attempt"

    ctx.db.begin()
    try:
        ctx.db.execute("DELETE FROM lesson_attempts WHERE profile_id=?", (student.id,))
        ctx.db.execute("DELETE FROM lesson_progress WHERE profile_id=?", (student.id,))
        ctx.db.execute("UPDATE profiles SET no_such_column=0 WHERE id=?", (student.id,))
    except sqlite3.OperationalError:
        ctx.db.rollback()
    else:  # pragma: no cover - the statement above is invalid by construction
        pytest.fail("expected the deliberate failure to raise")

    after = {
        "attempts": ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"],
        "progress": ctx.db.query("SELECT COUNT(*) AS c FROM lesson_progress")[0]["c"],
        "xp": ctx.db.query("SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"],
    }
    assert after == before, "the failed reset was partially applied"


@pytest.mark.xfail(strict=True, reason="defect D-04: score() runs six separate "
                                      "auto-committed writes, not one transaction")
def test_a_failure_while_scoring_leaves_no_partial_attempt(db, profile, attempt_factory):
    """DR-010: the attempt row, the progress cache, XP, the streak, the unlock and
    the badges are one logical event. If badge evaluation fails, the student must
    not be left with an attempt row and no XP."""
    ctx, student = profile
    attempt = attempt_factory(student.id)

    def explode(*_args, **_kwargs):
        raise RuntimeError("badge evaluation failed")

    ctx.badges.evaluate = explode

    with pytest.raises(RuntimeError):
        ctx.progression.score(attempt, student)

    assert ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 0
    assert ctx.db.query("SELECT total_xp FROM profiles WHERE id=?",
                        (student.id,))[0]["total_xp"] == 0
