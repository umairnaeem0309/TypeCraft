"""
managers/progression.py

Turns a finished TypingEngine result into persisted state: writes the
attempt row, updates the lesson_progress cache, awards XP/level, and
runs the D2 unlock check. This is the one place that writes a completed
attempt, so §2.2's "every aggregate query must filter status='complete'"
rule is enforced structurally, not by convention.
"""

from typecraft.engine import metrics as m
from typecraft.models.attempt import AttemptResult, AttemptStatus


class ProgressionService:
    def __init__(self, db, lesson_manager, badge_manager, streak_manager, profile_manager):
        self.db = db
        self.lesson_manager = lesson_manager
        self.badge_manager = badge_manager
        self.streak_manager = streak_manager
        self.profile_manager = profile_manager

    #: Profile fields score() mutates in memory. Snapshotted so a rolled-back
    #: transaction cannot leave the live Profile object disagreeing with the row on
    #: disk — otherwise the next successful save() would persist phantom XP.
    _MUTATED_PROFILE_FIELDS = (
        "total_xp", "level", "current_streak", "longest_streak", "last_active_date",
    )

    #: How often an active attempt is written to disk (FR-073). Long enough that
    #: typing never waits on the database, short enough that a power cut costs a
    #: child at most this many seconds of work.
    CHECKPOINT_INTERVAL_SEC = 10.0

    def checkpoint(self, engine, row_id: int = None) -> int:
        """Persist the in-flight attempt as `in_progress` and return its row id.

        Called on a timer from LessonScene.update(), never from feed_key() — a
        database write on the keystroke path would show up as stutter on a 4th-gen
        Intel machine (NFR-007).

        The first call reserves the row; later calls update that same row, so a
        crash can leave at most **one** row per attempt (ADR-004). score() then
        promotes the same row rather than inserting a second one.
        """
        attempt = engine.result(status=AttemptStatus.IN_PROGRESS)
        return self._write_attempt(attempt, row_id)

    def score(self, attempt: AttemptResult, profile, row_id: int = None) -> AttemptResult:
        """Persist the attempt and, if it is complete, apply everything that
        follows from it — progress cache, XP, level, streak, unlock, badges.

        All of it in **one transaction** (DR-010). These are not independent
        writes: an attempt row with no XP, or wiped progress with an intact level,
        is a state no screen can explain and no teacher can repair.
        """
        snapshot = {f: getattr(profile, f) for f in self._MUTATED_PROFILE_FIELDS}
        try:
            with self.db.transaction():
                self._write_attempt(attempt, row_id)

                if attempt.status != AttemptStatus.COMPLETE:
                    # D3: incomplete rows stop here — no progress/xp/streak/badges.
                    return attempt

                self._update_progress_cache(attempt)
                self._award_xp(profile, attempt.xp_awarded)
                self.streak_manager.touch(profile, _today())
                self.lesson_manager.unlock_next(profile, attempt.lesson_id, attempt.accuracy)
                self.badge_manager.evaluate(profile, attempt)
                self.profile_manager.save(profile)
        except BaseException:
            for field, value in snapshot.items():
                setattr(profile, field, value)
            raise

        return attempt

    def _write_attempt(self, attempt: AttemptResult, row_id: int = None) -> int:
        """Insert the attempt, or promote the row a checkpoint already reserved."""
        if row_id is not None:
            self.db.execute(
                """UPDATE lesson_attempts SET
                   status=?, mode=?, wpm_net=?, wpm_gross=?, accuracy=?, errors=?,
                   max_combo=?, duration_sec=?, stars=?, xp_awarded=?, completed_at=?,
                   total_keystrokes=?, correct_keystrokes=?, corrections_made=?
                   WHERE id=?""",
                (attempt.status.value, attempt.mode, attempt.wpm_net, attempt.wpm_gross,
                 attempt.accuracy, attempt.errors, attempt.max_combo, attempt.duration_sec,
                 attempt.stars, attempt.xp_awarded, attempt.completed_at,
                 attempt.total_keystrokes, attempt.correct_keystrokes,
                 attempt.corrections_made, row_id),
            )
            return row_id

        return self.db.execute(
            """INSERT INTO lesson_attempts
               (profile_id, lesson_id, status, mode, wpm_net, wpm_gross, accuracy,
                errors, max_combo, duration_sec, stars, xp_awarded, started_at, completed_at,
                total_keystrokes, correct_keystrokes, corrections_made)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (attempt.profile_id, attempt.lesson_id, attempt.status.value, attempt.mode,
             attempt.wpm_net, attempt.wpm_gross, attempt.accuracy, attempt.errors,
             attempt.max_combo, attempt.duration_sec, attempt.stars, attempt.xp_awarded,
             attempt.started_at, attempt.completed_at,
             attempt.total_keystrokes, attempt.correct_keystrokes, attempt.corrections_made),
        )

    def _update_progress_cache(self, attempt: AttemptResult) -> None:
        rows = self.db.query(
            "SELECT * FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
            (attempt.profile_id, attempt.lesson_id),
        )
        if not rows:
            self.db.execute(
                """INSERT INTO lesson_progress
                   (profile_id, lesson_id, is_unlocked, best_wpm_net, best_accuracy,
                    best_stars, times_completed)
                   VALUES (?, ?, 1, ?, ?, ?, 1)""",
                (attempt.profile_id, attempt.lesson_id, attempt.wpm_net,
                 attempt.accuracy, attempt.stars),
            )
            return

        current = rows[0]
        best_wpm = max(current["best_wpm_net"], attempt.wpm_net)
        best_acc = max(current["best_accuracy"], attempt.accuracy)
        best_stars = max(current["best_stars"], attempt.stars)
        self.db.execute(
            """UPDATE lesson_progress SET best_wpm_net=?, best_accuracy=?, best_stars=?,
               times_completed = times_completed + 1
               WHERE profile_id=? AND lesson_id=?""",
            (best_wpm, best_acc, best_stars, attempt.profile_id, attempt.lesson_id),
        )

    def _award_xp(self, profile, xp: int) -> None:
        profile.total_xp += xp
        profile.level = m.level_for(profile.total_xp)

    def xp_for(self, attempt: AttemptResult) -> int:
        return attempt.xp_awarded

    def level_for(self, total_xp: int) -> int:
        return m.level_for(total_xp)

    def stars_for(self, accuracy: float) -> int:
        return m.stars_for(accuracy)


def _today() -> str:
    import time
    return time.strftime("%Y-%m-%d")
