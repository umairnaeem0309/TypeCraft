"""
managers/progression.py

Turns a finished TypingEngine result into persisted state: writes the
attempt row, updates the lesson_progress cache, awards XP/level, and
runs the D2 unlock check. This is the one place that writes a completed
attempt, so §2.2's "every aggregate query must filter status='complete'"
rule is enforced structurally, not by convention.
"""

from TypeCraft.engine import metrics as m
from TypeCraft.models.attempt import AttemptResult, AttemptStatus


class ProgressionService:
    def __init__(self, db, lesson_manager, badge_manager, streak_manager, profile_manager):
        self.db = db
        self.lesson_manager = lesson_manager
        self.badge_manager = badge_manager
        self.streak_manager = streak_manager
        self.profile_manager = profile_manager

    def score(self, attempt: AttemptResult, profile) -> AttemptResult:
        """Persists the attempt (complete or incomplete per D3), and if
        complete, updates progress cache, XP/level, streak, and badges."""
        self.db.execute(
            """INSERT INTO lesson_attempts
               (profile_id, lesson_id, status, mode, wpm_net, wpm_gross, accuracy,
                errors, max_combo, duration_sec, stars, xp_awarded, started_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (attempt.profile_id, attempt.lesson_id, attempt.status.value, attempt.mode,
             attempt.wpm_net, attempt.wpm_gross, attempt.accuracy, attempt.errors,
             attempt.max_combo, attempt.duration_sec, attempt.stars, attempt.xp_awarded,
             attempt.started_at, attempt.completed_at),
        )

        if attempt.status != AttemptStatus.COMPLETE:
            return attempt  # D3: incomplete rows stop here — no progress/xp/streak/badges

        self._update_progress_cache(attempt)
        self._award_xp(profile, attempt.xp_awarded)
        self.streak_manager.touch(profile, _today())
        self.lesson_manager.unlock_next(profile, attempt.lesson_id, attempt.accuracy)
        self.badge_manager.evaluate(profile, attempt)
        self.profile_manager.save(profile)
        return attempt

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
