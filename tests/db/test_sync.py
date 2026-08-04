"""Offline student-results export/import tests."""

import json

import pytest

from typecraft.managers.database import Database
from typecraft.managers.sync_manager import SyncError, SyncManager


def _insert_source_data(db, name="S001_Ali"):
    profile_id = db.execute(
        """INSERT INTO profiles (name, avatar_key, total_xp, level, created_at)
           VALUES (?,?,?,?,?)""",
        (name, "avatar_fox", 125, 2, "2026-08-04T09:00:00"),
    )
    db.execute(
        """INSERT INTO lesson_progress
           (profile_id, lesson_id, is_unlocked, best_wpm_net, best_accuracy,
            best_stars, times_completed)
           VALUES (?,?,?,?,?,?,?)""",
        (profile_id, "t1l1", 1, 24.0, 96.0, 3, 1),
    )
    attempt_id = db.execute(
        """INSERT INTO lesson_attempts
           (profile_id, lesson_id, status, mode, wpm_net, wpm_gross, accuracy,
            errors, max_combo, duration_sec, stars, xp_awarded, started_at,
            completed_at, total_keystrokes, correct_keystrokes, corrections_made)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (profile_id, "t1l1", "complete", "lock_on_error", 24.0, 25.0, 96.0,
         4, 30, 60.0, 3, 125, "2026-08-04T09:00:00", "2026-08-04T09:01:00",
         100, 96, 0),
    )
    return profile_id, attempt_id


def test_export_contains_profiles_and_never_contains_teacher_settings(db, tmp_path):
    _insert_source_data(db)
    target = tmp_path / "student-results.json"

    SyncManager(db).export_results(target)
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["format"] == "typecraft-student-results"
    assert payload["source_database_id"] == db.database_id()
    assert payload["profiles"][0]["identity"] == "s001_ali"
    assert payload["profiles"][0]["attempts"][0]["lesson_id"] == "t1l1"
    assert "teacher_pin_hash" not in target.read_text(encoding="utf-8")


def test_import_creates_profile_and_is_idempotent(writable_dir, tmp_path):
    source = Database("source.db")
    target = Database("target.db")
    try:
        _insert_source_data(source)
        export_path = tmp_path / "machine-01.json"
        SyncManager(source).export_results(export_path)

        result = SyncManager(target).import_results(export_path)
        assert result == {
            "profiles_created": 1,
            "attempts_imported": 1,
            "attempts_skipped": 0,
        }
        assert target.query("SELECT COUNT(*) AS c FROM profiles")[0]["c"] == 1
        assert target.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1

        repeated = SyncManager(target).import_results(export_path)
        assert repeated["profiles_created"] == 0
        assert repeated["attempts_imported"] == 0
        assert repeated["attempts_skipped"] == 1
        assert target.query("SELECT COUNT(*) AS c FROM lesson_attempts")[0]["c"] == 1
    finally:
        source.close()
        target.close()


def test_import_matches_profile_by_stable_name_and_keeps_local_ids(writable_dir, tmp_path):
    source = Database("source.db")
    target = Database("target.db")
    try:
        _insert_source_data(source, "S001_Ali")
        local_id = target.execute(
            "INSERT INTO profiles (name, avatar_key, created_at) VALUES (?,?,?)",
            ("s001_ali", "avatar_owl", "2026-08-04T10:00:00"),
        )
        export_path = tmp_path / "machine-01.json"
        SyncManager(source).export_results(export_path)

        result = SyncManager(target).import_results(export_path)

        assert result["profiles_created"] == 0
        assert target.query("SELECT COUNT(*) AS c FROM profiles")[0]["c"] == 1
        assert target.query("SELECT profile_id FROM lesson_attempts")[0]["profile_id"] == local_id
        assert target.query("SELECT avatar_key FROM profiles")[0]["avatar_key"] == "avatar_owl"
    finally:
        source.close()
        target.close()


def test_import_rejects_current_database_export(db, tmp_path):
    _insert_source_data(db)
    export_path = tmp_path / "same.json"
    SyncManager(db).export_results(export_path)

    with pytest.raises(SyncError, match="current database"):
        SyncManager(db).import_results(export_path)


def test_import_rejects_invalid_export(db, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"format": "not-typecraft"}), encoding="utf-8")

    with pytest.raises(SyncError, match="not a TypeCraft"):
        SyncManager(db).import_results(path)
