"""
managers/database.py

sqlite3 wrapper + schema bootstrap. Every other manager talks to the DB
only through this class — nobody else imports sqlite3 directly.

The .db file lives in core.paths.writable_data_dir(), never inside the
PyInstaller bundle (blueprint §3.3) — that split is what stops student
progress from vanishing between runs.
"""

import sqlite3
from pathlib import Path

from typecraft.core.paths import writable_data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    avatar_key TEXT NOT NULL,
    total_xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    last_active_date TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lesson_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    wpm_net REAL NOT NULL DEFAULT 0,
    wpm_gross REAL NOT NULL DEFAULT 0,
    accuracy REAL NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    max_combo INTEGER NOT NULL DEFAULT 0,
    duration_sec REAL NOT NULL DEFAULT 0,
    stars INTEGER NOT NULL DEFAULT 0,
    xp_awarded INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_attempts_lookup
    ON lesson_attempts(profile_id, lesson_id, status);

CREATE TABLE IF NOT EXISTS lesson_progress (
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    lesson_id TEXT NOT NULL,
    is_unlocked INTEGER NOT NULL DEFAULT 0,
    best_wpm_net REAL NOT NULL DEFAULT 0,
    best_accuracy REAL NOT NULL DEFAULT 0,
    best_stars INTEGER NOT NULL DEFAULT 0,
    times_completed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (profile_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    xp_bonus INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profile_badges (
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    badge_id INTEGER NOT NULL REFERENCES badges(id),
    earned_at TEXT NOT NULL,
    PRIMARY KEY (profile_id, badge_id)
);
"""


class Database:
    def __init__(self, db_filename: str = "typecraft.db"):
        db_path = writable_data_dir() / db_filename
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._bootstrap()

    def _bootstrap(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._reclassify_orphaned_attempts()

    def _reclassify_orphaned_attempts(self) -> None:
        """Decision D3: any row still 'in_progress' at startup means the app
        crashed or lost power mid-lesson last time. Reclassify to
        'incomplete' so it's excluded from averages/leaderboard/unlock checks."""
        self._conn.execute(
            "UPDATE lesson_attempts SET status = 'incomplete' WHERE status = 'in_progress'"
        )
        self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list:
        cur = self._conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Runs an INSERT/UPDATE/DELETE, commits, returns lastrowid (for INSERT)."""
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur.lastrowid

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()
