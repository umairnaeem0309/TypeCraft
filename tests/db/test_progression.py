"""Scoring an attempt: persistence, the progress cache, XP and levels.

ProgressionService.score() is the single writer of an attempt, which is what makes
"every aggregate filters status='complete'" (FR-064) enforceable structurally
rather than by convention. These tests hold it to that.
"""

import pytest

from typecraft.engine import metrics as m
from typecraft.models.attempt import AttemptStatus


def _attempts(ctx, profile_id, status=None):
    sql = "SELECT * FROM lesson_attempts WHERE profile_id=?"
    params = [profile_id]
    if status:
        sql += " AND status=?"
        params.append(status)
    return ctx.db.query(sql, tuple(params))


def _progress(ctx, profile_id, lesson_id):
    rows = ctx.db.query(
        "SELECT * FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
        (profile_id, lesson_id),
    )
    return rows[0] if rows else None


def _xp(ctx, profile_id):
    return ctx.db.query("SELECT total_xp, level FROM profiles WHERE id=?", (profile_id,))[0]


# --------------------------------------------------------------------- profile creation

def test_new_profile_unlocks_exactly_the_first_lesson(profile):
    """FR-015: everything else stays locked until the 85 % bar is cleared."""
    ctx, student = profile
    unlocked = ctx.db.query(
        "SELECT lesson_id FROM lesson_progress WHERE profile_id=? AND is_unlocked=1",
        (student.id,),
    )
    first = ctx.lessons.first_lesson()
    assert [r["lesson_id"] for r in unlocked] == [first.id]
    assert ctx.lessons.is_unlocked(student, first.id) is True


def test_new_profile_starts_with_no_attempts_and_no_xp(profile):
    ctx, student = profile
    assert _attempts(ctx, student.id) == []
    assert _xp(ctx, student.id) == {"total_xp": 0, "level": 1}


def test_new_profile_progress_row_is_all_zeroes(profile):
    """The root cause of defect D-10: a fresh profile already has a
    lesson_progress row, so any leaderboard query that groups over that table
    without filtering times_completed > 0 lists students who have never finished
    a lesson. The query itself is fixed and tested in TC-012."""
    ctx, student = profile
    row = _progress(ctx, student.id, ctx.lessons.first_lesson().id)
    assert row["times_completed"] == 0
    assert row["best_wpm_net"] == 0
    assert row["best_accuracy"] == 0
    assert row["best_stars"] == 0


# --------------------------------------------------------------------- complete vs incomplete

def test_completed_attempt_is_persisted_with_its_metrics(profile, attempt_factory):
    ctx, student = profile
    attempt = attempt_factory(student.id, accuracy=95.0, wpm_net=20.0)

    ctx.progression.score(attempt, student)

    rows = _attempts(ctx, student.id)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "complete"
    assert row["accuracy"] == pytest.approx(95.0)
    assert row["wpm_net"] == pytest.approx(20.0)
    assert row["stars"] == 2
    assert row["completed_at"] != ""


def test_incomplete_attempt_is_persisted_but_changes_nothing_else(profile, attempt_factory):
    """FR-070/FR-076: an abandoned attempt is recorded for the teacher's benefit
    and must not touch progress, XP, streaks, or badges."""
    ctx, student = profile
    attempt = attempt_factory(student.id, status=AttemptStatus.INCOMPLETE)

    ctx.progression.score(attempt, student)

    rows = _attempts(ctx, student.id)
    assert len(rows) == 1 and rows[0]["status"] == "incomplete"
    assert rows[0]["xp_awarded"] == 0
    assert rows[0]["stars"] == 0

    assert _xp(ctx, student.id) == {"total_xp": 0, "level": 1}
    assert _progress(ctx, student.id, "t1l1")["times_completed"] == 0
    assert ctx.db.query("SELECT COUNT(*) AS c FROM profile_badges")[0]["c"] == 0
    assert student.current_streak == 0


def test_incomplete_attempts_are_excluded_from_averages(profile, attempt_factory):
    """FR-075. A student who abandons four attempts and finishes one at 95 % must
    average 95 %, not the mean of five rows."""
    ctx, student = profile
    for _ in range(4):
        ctx.progression.score(
            attempt_factory(student.id, accuracy=10.0, status=AttemptStatus.INCOMPLETE), student)
    ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    avg = ctx.db.query(
        "SELECT AVG(accuracy) AS a FROM lesson_attempts WHERE profile_id=? AND status='complete'",
        (student.id,),
    )[0]["a"]
    assert avg == pytest.approx(95.0)


# --------------------------------------------------------------------- progress cache

def test_progress_cache_records_the_first_completion(profile, attempt_factory):
    """FR-065."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=90.0, wpm_net=15.0), student)

    row = _progress(ctx, student.id, "t1l1")
    assert row["times_completed"] == 1
    assert row["best_accuracy"] == pytest.approx(90.0)
    assert row["best_wpm_net"] == pytest.approx(15.0)
    assert row["best_stars"] == 1


def test_progress_cache_keeps_the_best_of_each_metric(profile, attempt_factory):
    """A worse retry must not erase a personal best, and the count still rises."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=98.0, wpm_net=30.0), student)
    ctx.progression.score(attempt_factory(student.id, accuracy=86.0, wpm_net=12.0), student)

    row = _progress(ctx, student.id, "t1l1")
    assert row["times_completed"] == 2
    assert row["best_accuracy"] == pytest.approx(98.0)
    assert row["best_wpm_net"] == pytest.approx(30.0)
    assert row["best_stars"] == 3


def test_progress_cache_is_per_lesson(profile, attempt_factory):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=95.0), student)
    ctx.progression.score(attempt_factory(student.id, "t1l2", accuracy=88.0), student)

    assert _progress(ctx, student.id, "t1l1")["best_accuracy"] == pytest.approx(95.0)
    assert _progress(ctx, student.id, "t1l2")["best_accuracy"] == pytest.approx(88.0)


# --------------------------------------------------------------------- XP and levels

def test_xp_accumulates_across_attempts_and_is_persisted(profile, attempt_factory):
    ctx, student = profile
    first = attempt_factory(student.id, accuracy=95.0)
    ctx.progression.score(first, student)
    after_one = _xp(ctx, student.id)["total_xp"]

    second = attempt_factory(student.id, accuracy=95.0)
    ctx.progression.score(second, student)

    assert after_one >= first.xp_awarded          # attempt XP, plus any badge bonus
    assert _xp(ctx, student.id)["total_xp"] == after_one + second.xp_awarded


def test_level_is_recomputed_from_total_xp(profile, attempt_factory):
    """FR-056."""
    ctx, student = profile
    student.total_xp = 480
    ctx.profiles.save(student)

    ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    stored = _xp(ctx, student.id)
    assert stored["level"] == m.level_for(stored["total_xp"])
    assert stored["level"] >= 5


def test_failed_attempt_still_counts_as_completed_and_earns_participation_xp(
        profile, attempt_factory):
    """Below 85 % the lesson is not passed (0 stars, no unlock) but the attempt is
    still a completed attempt: it appears in averages and earns participation XP."""
    ctx, student = profile
    attempt = attempt_factory(student.id, accuracy=70.0)

    ctx.progression.score(attempt, student)

    assert attempt.stars == 0
    assert attempt.xp_awarded == m.xp_for(70.0, 20.0, 0, 1)
    assert _attempts(ctx, student.id, "complete") != []
    assert ctx.lessons.is_unlocked(student, "t1l2") is False


# --------------------------------------------------------------------- known defects

@pytest.mark.xfail(strict=True, reason="defect D-11: badge XP is added after the level has "
                                      "already been recomputed, so it does not take effect "
                                      "until the next attempt")
def test_badge_xp_raises_the_level_in_the_same_attempt(profile, attempt_factory):
    """FR-083. Sequence: 30 XP on the profile, then a completed attempt at 84 %
    (4 participation XP) which also earns First Steps (+25). 30+4+25 = 59, which
    is level 2. ProgressionService._award_xp() computes the level from 34 and
    BadgeManager.award() then adds the 25 behind its back, so the stored level
    stays 1 until some later attempt happens to recompute it."""
    ctx, student = profile
    student.total_xp = 30
    ctx.profiles.save(student)

    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)

    stored = _xp(ctx, student.id)
    assert stored["total_xp"] == 59, "First Steps (+25) should have been awarded"
    assert stored["level"] == 2, f"level {stored['level']} disagrees with {stored['total_xp']} XP"


@pytest.mark.xfail(strict=True, reason="defect D-31: the daily streak bonus is never awarded "
                                      "- metrics.daily_streak_bonus() has no caller")
def test_first_completed_lesson_of_the_day_awards_the_streak_bonus(profile, attempt_factory):
    """FR-057. The blueprint's own XP economy depends on this: level 10 (2 250 XP)
    is only reachable because lessons, badges *and* a daily streak bonus all
    contribute. `metrics.daily_streak_bonus()` is implemented and tested but
    nothing in the app calls it, so one of the three sources contributes nothing.

    Fresh profile, one completed attempt at 84 %: 4 participation XP + 25 for
    First Steps + 5 for reaching a 1-day streak = 34.
    """
    ctx, student = profile

    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)

    assert student.current_streak == 1, "streak should have been touched"
    assert _xp(ctx, student.id)["total_xp"] == 4 + 25 + m.daily_streak_bonus(1)
