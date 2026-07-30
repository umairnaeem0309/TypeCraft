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
    def __init__(self, db, lesson_manager, badge_manager, streak_manager, profile_manager,
                 on_badge_awarded=None):
        self.db = db
        self.lesson_manager = lesson_manager
        self.badge_manager = badge_manager
        self.streak_manager = streak_manager
        self.profile_manager = profile_manager
        # Optional callback so badge awards can trigger UI feedback (e.g. a
        # sound) without managers importing pygame or depending on AudioManager.
        self._on_badge_awarded = on_badge_awarded

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
                self._add_xp(profile, attempt.xp_awarded)

                # Blueprint §2.4's XP economy has three sources, and level 10
                # (2 250 XP) is only reachable with all three. The streak bonus was
                # the missing one (defect D-31): metrics.daily_streak_bonus() existed
                # but nothing called it.
                today = _today()
                first_lesson_today = profile.last_active_date != today
                self.streak_manager.touch(profile, today)
                if first_lesson_today:
                    self._add_xp(profile, m.daily_streak_bonus(profile.current_streak))

                self.lesson_manager.unlock_next(profile, attempt.lesson_id, attempt.accuracy)

                # Level must be current *before* badges are judged, because
                # rising_star and keyboard_master test it.
                self._recompute_level(profile)
                self._evaluate_badges(profile, attempt)

                # Badge bonuses are XP too, so the level may have moved again. That
                # used to be missed entirely (defect D-11): _award_xp() computed the
                # level and BadgeManager.award() then added its bonus behind it, so
                # badge XP did not count until some later attempt happened to
                # recompute. One extra pass — deliberately not a loop, so a badge
                # cannot cascade forever.
                if self._recompute_level(profile):
                    self._evaluate_badges(profile, attempt)
                    self._recompute_level(profile)

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

    def _add_xp(self, profile, xp: int) -> None:
        """Add XP without touching the level — the caller decides when to recompute,
        because badges add XP after the fact."""
        profile.total_xp += xp

    def _recompute_level(self, profile) -> bool:
        """Set the level from total XP. Returns True if it changed."""
        new_level = m.level_for(profile.total_xp)
        changed = new_level != profile.level
        profile.level = new_level
        return changed

    #: Allow-list of leaderboard sort columns. The key comes from the UI, the value
    #: never does — an identifier cannot be parameterised in SQL, so the only safe
    #: pattern is to map a fixed key onto a fixed column name (SR-006).
    LEADERBOARD_COLUMNS = {"wpm": "best_wpm_net", "accuracy": "best_accuracy"}

    def leaderboard(self, board: str, limit: int = 10) -> list:
        """Top `limit` students on one board (FR-110..FR-113).

        Reads the `lesson_progress` cache — one indexed row per lesson rather than
        a scan of every attempt (ADR-011) — and counts **only students who have
        actually completed something**. `times_completed` is incremented solely by
        a completed attempt, so it is the filter that makes FR-112 true: without it
        every profile appeared with a score of 0, because a row is seeded at profile
        creation, and a child who had never typed a word occupied a leaderboard slot.

        Ties break on score, then the earlier-created profile, then id — total and
        stable, so the board does not reshuffle between openings (FR-113).
        """
        column = self.LEADERBOARD_COLUMNS[board]   # KeyError = programmer error
        return self.db.query(
            f"""SELECT p.id AS profile_id, p.name AS name, MAX(lp.{column}) AS score
                FROM lesson_progress lp
                JOIN profiles p ON p.id = lp.profile_id
                WHERE lp.times_completed > 0
                GROUP BY lp.profile_id
                HAVING score > 0
                ORDER BY score DESC, p.created_at ASC, p.id ASC
                LIMIT ?""",
            (limit,),
        )

    #: One SQL fragment for "attempts that count", so no aggregate can forget it
    #: (FR-064). Every average, count and ranking in the app filters on this.
    COMPLETED = "status = 'complete'"

    def student_summary(self, profile_id: int) -> dict:
        """Everything the teacher dashboard shows for one student (FR-122).

        Averages are over **completed attempts only** and come back as `None` when
        there are none, so the UI can say so explicitly rather than printing a
        misleading 0 % for a child who has not finished a lesson yet (FR-123).

        `lessons_completed` counts *distinct* lessons: replaying lesson 1 twenty
        times is one lesson learned, not twenty.
        """
        rows = self.db.query(
            f"""SELECT p.id AS profile_id, p.name, p.avatar_key, p.total_xp, p.level,
                       p.current_streak, p.longest_streak,
                       (SELECT COUNT(*) FROM profile_badges pb
                          WHERE pb.profile_id = p.id) AS badge_count,
                       (SELECT COUNT(DISTINCT a.lesson_id) FROM lesson_attempts a
                          WHERE a.profile_id = p.id AND a.{self.COMPLETED})
                          AS lessons_completed,
                       (SELECT COUNT(*) FROM lesson_attempts a
                          WHERE a.profile_id = p.id AND a.{self.COMPLETED})
                          AS completed_attempts,
                       (SELECT AVG(a.wpm_net) FROM lesson_attempts a
                          WHERE a.profile_id = p.id AND a.{self.COMPLETED}) AS avg_wpm_net,
                       (SELECT AVG(a.accuracy) FROM lesson_attempts a
                          WHERE a.profile_id = p.id AND a.{self.COMPLETED}) AS avg_accuracy
                FROM profiles p WHERE p.id = ?""",
            (profile_id,),
        )
        if not rows:
            raise ValueError(f"no profile with id {profile_id}")
        return rows[0]

    def class_summary(self) -> list:
        """`student_summary` for every profile, ordered by name for a register."""
        ids = [r["id"] for r in self.db.query("SELECT id FROM profiles ORDER BY name, id")]
        return [self.student_summary(pid) for pid in ids]

    def _evaluate_badges(self, profile, attempt) -> None:
        """Run badge evaluation and notify the UI if anything new was earned."""
        newly_awarded = self.badge_manager.evaluate(profile, attempt)
        if newly_awarded and self._on_badge_awarded is not None:
            self._on_badge_awarded()

    def xp_for(self, attempt: AttemptResult) -> int:
        return attempt.xp_awarded

    def level_for(self, total_xp: int) -> int:
        return m.level_for(total_xp)

    def stars_for(self, accuracy: float) -> int:
        return m.stars_for(accuracy)


def _today() -> str:
    import time
    return time.strftime("%Y-%m-%d")
