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


# --------------------------------------------------------------------- migrations

def test_a_fresh_database_is_at_the_current_version(db):
    from typecraft.managers.database import SCHEMA_VERSION

    assert db.schema_version() == SCHEMA_VERSION


def test_migrating_a_v1_database_adds_the_columns_and_keeps_the_data(writable_dir):
    """DR-009. Simulates a real school machine: a v1 database holding a student
    and an attempt, opened by this build. Columns must appear, the version must
    advance, and not one existing value may change."""
    import sqlite3

    from typecraft.managers.database import SCHEMA, SCHEMA_VERSION, Database

    # Build a v1 database: the inherited schema, minus schema_meta and the three
    # new columns, exactly as the inherited build left it.
    path = writable_dir / "typecraft.db"
    raw = sqlite3.connect(str(path))
    v1_schema = ";".join(
        stmt for stmt in SCHEMA.split(";") if "schema_meta" not in stmt
    )
    raw.executescript(v1_schema)
    raw.execute("INSERT INTO profiles (name, avatar_key, created_at, total_xp) "
                "VALUES ('Amina','avatar_fox','2026-07-01T09:00:00', 175)")
    raw.execute("""INSERT INTO lesson_attempts
                   (profile_id, lesson_id, status, mode, accuracy, stars, started_at)
                   VALUES (1,'t1l1','complete','lock_on_error', 91.5, 1, '2026-07-01T09:05:00')""")
    raw.commit()
    raw.close()

    migrated = Database()
    try:
        assert migrated.schema_version() == SCHEMA_VERSION
        assert {"total_keystrokes", "correct_keystrokes", "corrections_made"} <= _columns(
            migrated, "lesson_attempts")

        profile = migrated.query("SELECT * FROM profiles")[0]
        assert (profile["name"], profile["total_xp"]) == ("Amina", 175)

        attempt = migrated.query("SELECT * FROM lesson_attempts")[0]
        assert attempt["accuracy"] == pytest.approx(91.5)
        assert attempt["stars"] == 1
        assert attempt["total_keystrokes"] == 0, "pre-existing rows get the column default"
    finally:
        migrated.close()


def test_migration_is_idempotent(db, writable_dir):
    """Opening the same database repeatedly must be a no-op after the first time."""
    from typecraft.managers.database import SCHEMA_VERSION, Database

    db.close()
    for _ in range(3):
        again = Database()
        assert again.schema_version() == SCHEMA_VERSION
        assert len(_columns(again, "lesson_attempts")) == 18
        again.close()


def test_keystroke_counts_survive_a_round_trip(profile, attempt_factory):
    """FR-050: what the engine counted is what the teacher can audit later."""
    ctx, student = profile
    attempt = attempt_factory(student.id, accuracy=90.0, total_keystrokes=250)

    ctx.progression.score(attempt, student)

    row = ctx.db.query("SELECT * FROM lesson_attempts WHERE profile_id=?", (student.id,))[0]
    assert row["total_keystrokes"] == attempt.total_keystrokes
    assert row["correct_keystrokes"] == attempt.correct_keystrokes
    assert row["errors"] == attempt.errors
    # The stored accuracy must be reproducible from the stored counters.
    assert row["correct_keystrokes"] + row["errors"] == row["total_keystrokes"]
    assert row["accuracy"] == pytest.approx(
        row["correct_keystrokes"] / row["total_keystrokes"] * 100.0, abs=0.5)


# --------------------------------------------------------------------- column contract

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
