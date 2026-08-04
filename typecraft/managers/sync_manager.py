"""managers/sync_manager.py — offline student-results export/import.

Exports contain student data only, never settings or the teacher PIN. Imports are
idempotent: the same export can be selected again without duplicating attempts.
The source database identity and local attempt IDs are kept in the export because
integer IDs are only meaningful inside their original SQLite database.
"""

from __future__ import annotations

import json
from pathlib import Path


EXPORT_FORMAT = "typecraft-student-results"
EXPORT_VERSION = 1


class SyncError(ValueError):
    """A user-correctable export/import problem."""


def profile_key(name: str) -> str:
    """Return the stable classroom identity used to match profiles."""
    return " ".join(str(name).strip().split()).casefold()


class SyncManager:
    def __init__(self, db):
        self.db = db

    def export_results(self, path: str | Path) -> Path:
        """Write every local profile and its progress to a portable JSON file."""
        target = Path(path)
        profiles = self.db.query("SELECT * FROM profiles ORDER BY id")
        exported_profiles = []
        for profile in profiles:
            key = profile_key(profile["name"])
            if not key:
                raise SyncError("A profile has no usable name and cannot be exported.")
            attempts = self.db.query(
                "SELECT * FROM lesson_attempts WHERE profile_id=? ORDER BY id",
                (profile["id"],),
            )
            progress = self.db.query(
                "SELECT * FROM lesson_progress WHERE profile_id=? ORDER BY lesson_id",
                (profile["id"],),
            )
            badges = self.db.query(
                """SELECT b.code, pb.earned_at
                   FROM profile_badges pb JOIN badges b ON b.id=pb.badge_id
                   WHERE pb.profile_id=? ORDER BY b.code""",
                (profile["id"],),
            )
            exported_profiles.append({
                "identity": key,
                "profile": {
                    "name": profile["name"],
                    "avatar_key": profile["avatar_key"],
                    "total_xp": profile["total_xp"],
                    "level": profile["level"],
                    "current_streak": profile["current_streak"],
                    "longest_streak": profile["longest_streak"],
                    "last_active_date": profile["last_active_date"],
                    "created_at": profile["created_at"],
                },
                "attempts": [dict(row) for row in attempts],
                "progress": [dict(row) for row in progress],
                "badges": [dict(row) for row in badges],
            })

        payload = {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "source_database_id": self.db.database_id(),
            "profiles": exported_profiles,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def import_results(self, path: str | Path) -> dict:
        """Merge one export into this database and return an import summary.

        Profiles are matched by their stable profile identity (normally a code
        such as ``S001_Ali``). Attempts are recorded in ``sync_records`` before
        returning, so importing the same USB file repeatedly is safe.
        """
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SyncError(f"Could not read export file: {exc}") from exc

        self._validate_payload(payload)
        source_id = payload["source_database_id"]
        if source_id == self.db.database_id():
            raise SyncError("This export came from the current database.")

        imported_profiles = 0
        imported_attempts = 0
        skipped_attempts = 0
        with self.db.transaction():
            for item in payload["profiles"]:
                identity = item["identity"]
                profile_data = item["profile"]
                target_profile = self._find_profile(identity)
                if target_profile is None:
                    target_profile_id = self.db.execute(
                        """INSERT INTO profiles
                           (name, avatar_key, total_xp, level, current_streak,
                            longest_streak, last_active_date, created_at)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            profile_data["name"], profile_data["avatar_key"],
                            profile_data["total_xp"], profile_data["level"],
                            profile_data["current_streak"], profile_data["longest_streak"],
                            profile_data["last_active_date"], profile_data["created_at"],
                        ),
                    )
                    imported_profiles += 1
                else:
                    target_profile_id = target_profile["id"]
                    self._merge_profile(target_profile_id, profile_data)

                self._merge_progress(target_profile_id, item["progress"])
                self._merge_badges(target_profile_id, item["badges"])

                for attempt in item["attempts"]:
                    already = self.db.query(
                        """SELECT target_attempt_id FROM sync_records
                           WHERE source_database_id=? AND source_attempt_id=?""",
                        (source_id, attempt["id"]),
                    )
                    if already:
                        skipped_attempts += 1
                        continue
                    target_attempt_id = self._insert_attempt(target_profile_id, attempt)
                    self.db.execute(
                        """INSERT INTO sync_records
                           (source_database_id, source_attempt_id, target_attempt_id)
                           VALUES (?,?,?)""",
                        (source_id, attempt["id"], target_attempt_id),
                    )
                    imported_attempts += 1

        return {
            "profiles_created": imported_profiles,
            "attempts_imported": imported_attempts,
            "attempts_skipped": skipped_attempts,
        }

    def _validate_payload(self, payload: object) -> None:
        if not isinstance(payload, dict) or payload.get("format") != EXPORT_FORMAT:
            raise SyncError("This is not a TypeCraft student-results export.")
        if payload.get("version") != EXPORT_VERSION:
            raise SyncError("This export was made by an unsupported TypeCraft version.")
        if not isinstance(payload.get("source_database_id"), str) or not payload["source_database_id"]:
            raise SyncError("The export has no valid source database identity.")
        if not isinstance(payload.get("profiles"), list):
            raise SyncError("The export has no valid profile list.")
        identities = set()
        for item in payload["profiles"]:
            if not isinstance(item, dict) or not isinstance(item.get("profile"), dict):
                raise SyncError("The export contains an invalid profile.")
            identity = item.get("identity")
            if not isinstance(identity, str) or not identity or identity in identities:
                raise SyncError("The export contains duplicate or invalid profile identities.")
            identities.add(identity)
            for key in ("attempts", "progress", "badges"):
                if not isinstance(item.get(key), list):
                    raise SyncError(f"The export profile has no valid {key} list.")

    def _find_profile(self, identity: str):
        rows = self.db.query("SELECT * FROM profiles ORDER BY id")
        matches = [row for row in rows if profile_key(row["name"]) == identity]
        if len(matches) > 1:
            raise SyncError(f"Multiple local profiles match '{identity}'. Use unique profile codes.")
        return matches[0] if matches else None

    def _merge_profile(self, profile_id: int, source: dict) -> None:
        """Keep the strongest aggregate values when a profile already exists."""
        current = self.db.query("SELECT * FROM profiles WHERE id=?", (profile_id,))[0]
        last_active = max(current["last_active_date"] or "", source["last_active_date"] or "") or None
        self.db.execute(
            """UPDATE profiles SET total_xp=?, level=?, current_streak=?,
               longest_streak=?, last_active_date=? WHERE id=?""",
            (
                max(current["total_xp"], source["total_xp"]),
                max(current["level"], source["level"]),
                max(current["current_streak"], source["current_streak"]),
                max(current["longest_streak"], source["longest_streak"]),
                last_active,
                profile_id,
            ),
        )

    def _merge_progress(self, profile_id: int, rows: list) -> None:
        for row in rows:
            current = self.db.query(
                "SELECT * FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
                (profile_id, row["lesson_id"]),
            )
            if not current:
                self.db.execute(
                    """INSERT INTO lesson_progress
                       (profile_id, lesson_id, is_unlocked, best_wpm_net,
                        best_accuracy, best_stars, times_completed)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        profile_id, row["lesson_id"], row["is_unlocked"],
                        row["best_wpm_net"], row["best_accuracy"], row["best_stars"],
                        row["times_completed"],
                    ),
                )
                continue
            old = current[0]
            self.db.execute(
                """UPDATE lesson_progress SET is_unlocked=?, best_wpm_net=?,
                   best_accuracy=?, best_stars=?, times_completed=?
                   WHERE profile_id=? AND lesson_id=?""",
                (
                    max(old["is_unlocked"], row["is_unlocked"]),
                    max(old["best_wpm_net"], row["best_wpm_net"]),
                    max(old["best_accuracy"], row["best_accuracy"]),
                    max(old["best_stars"], row["best_stars"]),
                    max(old["times_completed"], row["times_completed"]),
                    profile_id, row["lesson_id"],
                ),
            )

    def _merge_badges(self, profile_id: int, rows: list) -> None:
        for row in rows:
            badges = self.db.query("SELECT id FROM badges WHERE code=?", (row["code"],))
            if not badges:
                continue
            self.db.execute(
                """INSERT OR IGNORE INTO profile_badges (profile_id, badge_id, earned_at)
                   VALUES (?,?,?)""",
                (profile_id, badges[0]["id"], row["earned_at"]),
            )

    def _insert_attempt(self, profile_id: int, attempt: dict) -> int:
        columns = (
            "profile_id", "lesson_id", "status", "mode", "wpm_net", "wpm_gross",
            "accuracy", "errors", "max_combo", "duration_sec", "stars", "xp_awarded",
            "started_at", "completed_at", "total_keystrokes", "correct_keystrokes",
            "corrections_made",
        )
        values = [profile_id] + [attempt[column] for column in columns[1:]]
        placeholders = ",".join("?" for _ in values)
        return self.db.execute(
            f"INSERT INTO lesson_attempts ({','.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
