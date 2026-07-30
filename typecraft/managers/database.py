"""
managers/database.py

sqlite3 wrapper + schema bootstrap. Every other manager talks to the DB
only through this class — nobody else imports sqlite3 directly.

The .db file lives in core.paths.writable_data_dir(), never inside the
PyInstaller bundle (blueprint §3.3) — that split is what stops student
progress from vanishing between runs.
"""

import sqlite3
from contextlib import contextmanager

from typecraft.core.paths import writable_data_dir

#: Bumped whenever _migrate() gains a step. v1 = the inherited schema.
SCHEMA_VERSION = 2

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

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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

        # isolation_level=None puts the driver in autocommit mode: a single
        # statement commits on its own, and a multi-statement change is opened
        # explicitly by transaction(). With the driver's default isolation level
        # it opens transactions behind our back and execute()'s commit ended them
        # early, so begin()/rollback() could not undo anything — defect D-04, the
        # reason the teacher's reset-progress was never actually atomic.
        self._conn = sqlite3.connect(str(db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._in_txn = False

        self._conn.execute("PRAGMA foreign_keys = ON")
        # Durability over write throughput: fsync on every commit, so a power cut
        # mid-lesson cannot lose an already-committed attempt. There is one local
        # single-user process, so the cost is irrelevant.
        self._conn.execute("PRAGMA synchronous = FULL")
        # Deliberately the default rollback journal, NOT WAL (ADR-012): in WAL mode
        # recently-committed rows can live in typecraft.db-wal rather than the main
        # file, so a teacher copying typecraft.db to a USB stick after a crash would
        # silently lose them. The rollback journal deletes itself on commit, which
        # keeps the .db file a complete snapshot and DR-014's one-file backup honest.
        self._conn.execute("PRAGMA journal_mode = DELETE")

        self._bootstrap()

    def _bootstrap(self) -> None:
        # executescript() manages its own transaction, so it runs outside ours.
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._reclassify_orphaned_attempts()

    # --- Migrations --------------------------------------------------------
    # Additive and idempotent only (DR-009): a school machine's typecraft.db
    # already holds real student records, so a migration may add columns with
    # defaults but must never drop, rename, or rewrite one. An older build
    # opening a newer database simply ignores columns it does not know about.

    def schema_version(self) -> int:
        rows = self.query("SELECT value FROM schema_meta WHERE key='schema_version'")
        return int(rows[0]["value"]) if rows else 1

    def _migrate(self) -> None:
        current = self.schema_version()
        if current >= SCHEMA_VERSION:
            self._set_schema_version(SCHEMA_VERSION)
            return

        with self.transaction():
            if current < 2:
                # FR-050/DR-003: AttemptResult has carried these three counters
                # all along, but the table had nowhere to put them, so every
                # stored accuracy figure was unauditable (defect D-09).
                self._add_column("lesson_attempts", "total_keystrokes",
                                 "INTEGER NOT NULL DEFAULT 0")
                self._add_column("lesson_attempts", "correct_keystrokes",
                                 "INTEGER NOT NULL DEFAULT 0")
                self._add_column("lesson_attempts", "corrections_made",
                                 "INTEGER NOT NULL DEFAULT 0")
            self._set_schema_version(SCHEMA_VERSION)

    def _add_column(self, table: str, column: str, definition: str) -> None:
        existing = {r["name"] for r in self.query(f"PRAGMA table_info({table})")}
        if column not in existing:
            # Table and column names are module constants, never input (SR-006).
            self.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _set_schema_version(self, version: int) -> None:
        self.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(version),),
        )

    def _reclassify_orphaned_attempts(self) -> None:
        """Decision D3: any row still 'in_progress' at startup means the app
        crashed or lost power mid-lesson last time. Reclassify to
        'incomplete' so it's excluded from averages/leaderboard/unlock checks."""
        self.execute(
            "UPDATE lesson_attempts SET status = 'incomplete' WHERE status = 'in_progress'"
        )

    def query(self, sql: str, params: tuple = ()) -> list:
        cur = self._conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Runs one INSERT/UPDATE/DELETE and returns lastrowid (for INSERT).

        Outside a transaction the statement commits on its own. Inside one it
        does not — that is what makes transaction() able to roll the whole group
        back.
        """
        cur = self._conn.execute(sql, params)
        return cur.lastrowid

    @contextmanager
    def transaction(self):
        """Run a group of statements as one all-or-nothing change (DR-010).

            with db.transaction():
                db.execute(...)
                db.execute(...)

        Commits on a clean exit; rolls back and re-raises on any exception, so a
        caller can never accidentally swallow a half-applied write. Refuses to
        nest, because a nested `with` would silently commit the outer block early
        and reintroduce exactly the bug this replaces.
        """
        if self._in_txn:
            raise RuntimeError(
                "Database.transaction() cannot be nested — the inner block would "
                "commit the outer one early. Pass the work down inside one transaction."
            )

        self._conn.execute("BEGIN IMMEDIATE")
        self._in_txn = True
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            self._in_txn = False
            raise
        self._conn.execute("COMMIT")
        self._in_txn = False

    @property
    def in_transaction(self) -> bool:
        return self._in_txn

    # --- Explicit transaction control -------------------------------------
    # transaction() is the preferred API. These remain for call sites that
    # cannot use a `with` block, and unlike the originals they actually work.

    def begin(self) -> None:
        if self._in_txn:
            raise RuntimeError("a transaction is already open")
        self._conn.execute("BEGIN IMMEDIATE")
        self._in_txn = True

    def commit(self) -> None:
        if self._in_txn:
            self._conn.execute("COMMIT")
            self._in_txn = False

    def rollback(self) -> None:
        if self._in_txn:
            self._conn.execute("ROLLBACK")
            self._in_txn = False

    def close(self) -> None:
        # An open transaction at shutdown means something went wrong mid-write;
        # discard it rather than letting sqlite decide.
        self.rollback()
        self._conn.close()
