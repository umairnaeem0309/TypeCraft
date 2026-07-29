"""Transaction boundaries (DR-010).

Two multi-statement mutations must be all-or-nothing: scoring a completed attempt
(attempt row + progress cache + XP + streak + unlock + badges) and resetting one
student (delete attempts + progress + badges, zero XP/level/streaks, re-unlock
lesson 1). A failure part-way through either one leaves a child's record in a
state no screen can explain — half-wiped progress with intact XP, or the reverse.

Before TC-008, `Database.execute()` committed after *every* statement, so the
enclosing `begin()` was over before the second statement ran and `rollback()` had
nothing to undo — defect D-04, which made
`TeacherDashboardScene._reset_progress` not the atomic operation its
`try/except: rollback(); raise` implied. The connection now runs in autocommit
mode with an explicit `transaction()` context manager.
"""

import sqlite3

import pytest


def _profile_count(db):
    return db.query("SELECT COUNT(*) AS c FROM profiles")[0]["c"]


def test_a_single_statement_is_durable(db):
    """The autocommit path must keep working — most writes are single statements."""
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    assert _profile_count(db) == 1


def test_rollback_undoes_every_statement_since_begin(db):
    """The property the teacher's reset depends on."""
    db.begin()
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('B','x','t')")
    db.rollback()

    assert _profile_count(db) == 0


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


# --------------------------------------------------------------------- the new contract

def test_transaction_commits_on_a_clean_exit(db):
    with db.transaction():
        db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
        db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('B','x','t')")

    assert _profile_count(db) == 2
    assert db.in_transaction is False


def test_transaction_rolls_back_and_re_raises(db):
    """Re-raising matters: a caller must not be able to swallow the failure and
    carry on believing the write happened."""
    with pytest.raises(RuntimeError, match="boom"):
        with db.transaction():
            db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
            raise RuntimeError("boom")

    assert _profile_count(db) == 0
    assert db.in_transaction is False


def test_transaction_rolls_back_on_a_sql_error(db):
    import sqlite3

    with pytest.raises(sqlite3.OperationalError):
        with db.transaction():
            db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
            db.execute("UPDATE profiles SET no_such_column = 1")

    assert _profile_count(db) == 0


def test_nesting_a_transaction_is_refused(db):
    """A nested `with` would commit the outer block early — exactly the bug D-04
    was. Better to fail loudly than to silently half-commit."""
    with pytest.raises(RuntimeError, match="cannot be nested"):
        with db.transaction():
            with db.transaction():
                pass


def test_a_refused_nesting_does_not_abandon_the_outer_transaction(db):
    """The outer block must still roll back cleanly after the nesting error."""
    with pytest.raises(RuntimeError, match="cannot be nested"):
        with db.transaction():
            db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
            with db.transaction():
                pass

    assert _profile_count(db) == 0
    assert db.in_transaction is False


def test_statements_outside_a_transaction_still_commit_immediately(db, writable_dir):
    """Most writes are single statements and must not need ceremony. Verified by
    reopening the file rather than by trusting the same connection."""
    from typecraft.managers.database import Database

    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.close()

    reopened = Database()
    try:
        assert _profile_count(reopened) == 1
    finally:
        reopened.close()


def test_a_committed_transaction_survives_reopening(db, writable_dir):
    """DR-010 + DR-014: durability is what the whole exercise is for."""
    from typecraft.managers.database import Database

    with db.transaction():
        db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.close()

    reopened = Database()
    try:
        assert _profile_count(reopened) == 1
    finally:
        reopened.close()


def test_closing_with_an_open_transaction_discards_it(db, writable_dir):
    """An open transaction at shutdown means something went wrong mid-write.
    Discard it explicitly rather than leaving the outcome to sqlite."""
    from typecraft.managers.database import Database

    db.begin()
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.close()

    reopened = Database()
    try:
        assert _profile_count(reopened) == 0
    finally:
        reopened.close()


def test_the_journal_mode_is_not_wal(db):
    """ADR-012. In WAL mode committed rows can live in typecraft.db-wal, so a
    teacher copying typecraft.db to a USB stick after a crash would silently lose
    them — breaking DR-014's one-file backup story."""
    mode = db.query("PRAGMA journal_mode")[0]["journal_mode"]
    assert mode.lower() != "wal"


def test_commits_are_synchronous(db):
    """ADR-012: fsync on every commit, so a power cut cannot lose a committed
    attempt. 2 == FULL."""
    assert db.query("PRAGMA synchronous")[0]["synchronous"] == 2


def test_a_rolled_back_score_leaves_the_in_memory_profile_unchanged(profile, attempt_factory):
    """Subtle but important: BadgeManager.award() and _award_xp() mutate the live
    Profile object. If the transaction rolls back but those mutations stay, the
    next successful save() writes phantom XP that was never earned."""
    ctx, student = profile
    before = (student.total_xp, student.level, student.current_streak,
              student.longest_streak, student.last_active_date)

    def explode(*_a, **_k):
        raise RuntimeError("badge evaluation failed")

    ctx.badges.evaluate = explode
    with pytest.raises(RuntimeError):
        ctx.progression.score(attempt_factory(student.id), student)

    assert (student.total_xp, student.level, student.current_streak,
            student.longest_streak, student.last_active_date) == before


def test_reset_progress_is_atomic_and_keeps_the_profile(profile, attempt_factory):
    """FR-126/FR-127, exercised through the real dashboard method."""
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    assert ctx.lessons.is_unlocked(student, "t1l2") is True

    scene = TeacherDashboardScene(ctx)
    scene._reset_progress(student)

    assert ctx.db.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 0
    assert ctx.db.query("SELECT COUNT(*) AS c FROM profile_badges")[0]["c"] == 0
    row = ctx.db.query("SELECT * FROM profiles WHERE id=?", (student.id,))[0]
    assert row["name"] == "Test Student", "the child's profile must survive a reset"
    assert (row["total_xp"], row["level"], row["current_streak"]) == (0, 1, 0)

    # Lesson 1 unlocked again, and only lesson 1.
    unlocked = {r["lesson_id"] for r in ctx.db.query(
        "SELECT lesson_id FROM lesson_progress WHERE profile_id=? AND is_unlocked=1",
        (student.id,))}
    assert unlocked == {ctx.lessons.first_lesson().id}
