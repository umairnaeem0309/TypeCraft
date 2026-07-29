"""Schema bootstrap, indexes, and crash recovery at startup (DR-002, DR-007, DR-008, FR-074).

All against a real temporary SQLite file, never the developer's database — see
tests/conftest.py for how the writable directory is redirected.
"""

import pytest

from typecraft.managers.database import Database

EXPECTED_TABLES = {"profiles", "lesson_attempts", "lesson_progress", "badges", "profile_badges"}


def _columns(db, table):
    return {row["name"] for row in db.query(f"PRAGMA table_info({table})")}


def test_bootstrap_creates_every_table(db):
    """DR-002."""
    tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= tables


def test_bootstrap_is_idempotent_and_never_destroys_data(db, writable_dir):
    """DR-008: opening an existing database must not wipe it. This is the property
    that lets the app be restarted, and an update be installed, without loss."""
    db.execute(
        "INSERT INTO profiles (name, avatar_key, created_at) VALUES (?,?,?)",
        ("Amina", "avatar_fox", "2026-07-29T09:00:00"),
    )
    db.close()

    reopened = Database()  # same file: writable_dir is redirected for the whole test
    try:
        rows = reopened.query("SELECT name FROM profiles")
        assert [r["name"] for r in rows] == ["Amina"]
    finally:
        reopened.close()


def test_attempt_lookup_index_exists(db):
    """DR-007: the lesson-select grid and the unlock check read this index instead
    of scanning every attempt — a deliberate low-end-hardware choice."""
    indexes = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_attempts_lookup" in indexes


def test_lesson_progress_is_keyed_by_profile_and_lesson(db):
    """DR-007: the composite primary key must reject a duplicate row."""
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.execute(
        "INSERT INTO lesson_progress (profile_id, lesson_id, is_unlocked) VALUES (1,'t1l1',1)")
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO lesson_progress (profile_id, lesson_id, is_unlocked) VALUES (1,'t1l1',1)")


def test_badge_codes_are_unique(db):
    """A badge must not be insertable twice under the same code, which is what
    makes BadgeManager's catalogue sync idempotent."""
    import sqlite3

    db.execute("INSERT INTO badges (code, name, description) VALUES ('x','X','d')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO badges (code, name, description) VALUES ('x','X2','d2')")


# --------------------------------------------------------------------- crash recovery

def test_orphaned_in_progress_attempts_are_reclassified_on_startup(db, writable_dir):
    """FR-074: a row still 'in_progress' means the app was killed or lost power
    mid-lesson. On the next start it must become 'incomplete' so it is excluded
    from averages, the leaderboard, and unlock checks."""
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    db.execute(
        """INSERT INTO lesson_attempts
           (profile_id, lesson_id, status, mode, started_at)
           VALUES (1, 't1l1', 'in_progress', 'lock_on_error', '2026-07-29T09:00:00')"""
    )
    db.close()

    reopened = Database()
    try:
        statuses = [r["status"] for r in reopened.query("SELECT status FROM lesson_attempts")]
        assert statuses == ["incomplete"]
    finally:
        reopened.close()


def test_reclassification_leaves_complete_and_incomplete_rows_alone(db, writable_dir):
    """Recovery must not rewrite history it did not create."""
    db.execute("INSERT INTO profiles (name, avatar_key, created_at) VALUES ('A','x','t')")
    for status in ("complete", "incomplete", "in_progress"):
        db.execute(
            """INSERT INTO lesson_attempts (profile_id, lesson_id, status, mode, started_at)
               VALUES (1, 't1l1', ?, 'lock_on_error', 's')""",
            (status,),
        )
    db.close()

    reopened = Database()
    try:
        counts = {r["status"]: r["c"] for r in reopened.query(
            "SELECT status, COUNT(*) AS c FROM lesson_attempts GROUP BY status")}
        assert counts == {"complete": 1, "incomplete": 2}
    finally:
        reopened.close()


# --------------------------------------------------------------------- known defect

@pytest.mark.xfail(strict=True, reason="defect D-09: lesson_attempts has no "
                                      "total_keystrokes / correct_keystrokes columns")
def test_attempts_table_stores_the_keystroke_counts(db):
    """FR-050/DR-003. AttemptResult already carries these three counters and the
    engine computes them, but the table has nowhere to put them, so
    ProgressionService.score() silently drops them and no audit of a stored
    accuracy figure is possible. TC-008b adds them by migration."""
    from typecraft.models.attempt import AttemptResult

    columns = _columns(db, "lesson_attempts")

    required = {"total_keystrokes", "correct_keystrokes", "corrections_made"}
    assert required <= columns, f"missing: {sorted(required - columns)}"

    # The table must stay a superset of what the engine produces (ARCHITECTURE 17).
    engine_fields = set(AttemptResult.__dataclass_fields__) - {"char_statuses", "status"}
    assert engine_fields - {"combo"} <= columns
