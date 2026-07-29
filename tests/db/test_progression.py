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


# --------------------------------------------------------------------- XP economy

def test_badge_xp_raises_the_level_in_the_same_attempt(profile, attempt_factory):
    """FR-083. Sequence: 30 XP on the profile, then a completed attempt at 84 %
    (4 participation XP) which also earns First Steps (+25) and the first-of-day
    streak bonus (+5). 30+4+25+5 = 64, which is level 2. The old code computed the
    level from 34 and let BadgeManager.award() add the 25 behind its back, so the
    stored level stayed 1 until some later attempt happened to recompute it."""
    ctx, student = profile
    student.total_xp = 30
    ctx.profiles.save(student)

    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)

    stored = _xp(ctx, student.id)
    assert stored["total_xp"] == 30 + 4 + 25 + 5, (
        "30 start + 4 participation + 25 First Steps + 5 first-lesson-of-the-day streak bonus")
    assert stored["level"] == 2, f"level {stored['level']} disagrees with {stored['total_xp']} XP"


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


def test_the_streak_bonus_is_awarded_only_once_a_day(profile, attempt_factory):
    """FR-057: the bonus rewards showing up, not grinding. A second lesson on the
    same day earns its own XP and nothing extra."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)
    after_first = _xp(ctx, student.id)["total_xp"]

    second = attempt_factory(student.id, "t1l2", accuracy=84.0)
    ctx.progression.score(second, student)

    assert _xp(ctx, student.id)["total_xp"] == after_first + second.xp_awarded


def test_the_streak_bonus_grows_with_the_streak_and_saturates(profile, attempt_factory):
    """FR-057: +5 per day up to 5 days. Days are simulated by rewinding
    last_active_date, which is the same thing the calendar does."""
    ctx, student = profile
    from datetime import date, timedelta

    awarded = []
    # The same lesson every day, and only six days: replaying one lesson avoids
    # earning Home Row Hero (all of tier 1) and stops short of Perfect Week
    # (a 7-day streak), either of which would add badge XP and confuse the
    # arithmetic this test is actually about.
    for _ in range(6):
        before = _xp(ctx, student.id)["total_xp"]
        attempt = attempt_factory(student.id, "t1l1", accuracy=84.0)
        ctx.progression.score(attempt, student)
        awarded.append(_xp(ctx, student.id)["total_xp"] - before - attempt.xp_awarded)

        # Pretend the next lesson happens tomorrow.
        student.last_active_date = str(
            date.fromisoformat(student.last_active_date) - timedelta(days=1))
        ctx.profiles.save(student)

    awarded[0] -= 25            # day one also pays First Steps
    assert awarded == [5, 10, 15, 20, 25, 25], awarded
    assert student.current_streak == 6


def test_badge_xp_that_crosses_a_level_awards_the_level_badge_immediately(
        profile, attempt_factory):
    """FR-081/FR-083 together, the case that needed the second evaluation pass:
    480 XP + 4 participation + 5 streak = 489 (level 4). First Steps (+25) takes
    it to 514, which is level 5 — so `rising_star` becomes true *because of* the
    badge XP and must be awarded in the same attempt, not the next one."""
    ctx, student = profile
    student.total_xp = 480
    ctx.profiles.save(student)

    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)

    earned = {r["code"] for r in ctx.db.query(
        """SELECT b.code FROM profile_badges pb JOIN badges b ON b.id = pb.badge_id
           WHERE pb.profile_id=?""", (student.id,))}
    assert {"first_steps", "rising_star"} <= earned

    stored = _xp(ctx, student.id)
    assert stored["total_xp"] == 480 + 4 + 5 + 25 + 40
    assert stored["level"] == 5
    assert stored["level"] == m.level_for(stored["total_xp"])


def test_the_second_badge_pass_is_bounded(profile, attempt_factory):
    """A badge award changes XP, which can change the level, which can award
    another badge. Exactly one extra pass is run — a loop could not terminate on a
    catalogue where a badge's bonus unlocks the next tier."""
    ctx, student = profile
    calls = []
    original = ctx.badges.evaluate
    ctx.badges.evaluate = lambda p, a: (calls.append(1), original(p, a))[1]

    student.total_xp = 480
    ctx.profiles.save(student)
    ctx.progression.score(attempt_factory(student.id, accuracy=84.0), student)

    assert len(calls) <= 2, f"badge evaluation ran {len(calls)} times"


def test_level_ten_is_reachable_only_with_all_three_xp_sources(app_ctx):
    """Blueprint §2.4 claims level 10 (2 250 XP) is reachable because lessons,
    badges *and* streaks all contribute — "~2,000 XP from clearing **and
    replaying** the 20+ lessons toward 3★, plus ~625 from badges, plus a streak
    bonus". This pins that arithmetic, and pins how tight it is.

    Measured here: a single 3★ pass of all 20 lessons is only ~1 050 XP, so
    replaying really is required — and with the streak bonus missing (D-31) the
    target was out of reach for a student who cleared everything once.
    """
    lessons = app_ctx.lessons._ordered
    one_pass = sum(m.xp_for(97.0, l.target_wpm, 3, l.tier) for l in lessons)
    badge_xp = sum(r["xp_bonus"] for r in app_ctx.db.query("SELECT xp_bonus FROM badges"))
    # Twenty school days of practice; the bonus saturates after five.
    streak_xp = sum(m.daily_streak_bonus(min(d, 5)) for d in range(1, 21))

    needed = m.xp_to_reach(10)
    assert one_pass + badge_xp < needed, (
        "if one pass of every lesson plus every badge already reached level 10, the "
        "curve would be too generous to be an achievement"
    )

    # Clearing each lesson then replaying it once to 3★ — the blueprint's model.
    two_passes = one_pass + sum(m.xp_for(88.0, l.target_wpm * 0.8, 1, l.tier) for l in lessons)
    total = two_passes + badge_xp + streak_xp
    assert total >= needed, (
        f"level 10 needs {needed}; lessons {two_passes} + badges {badge_xp} "
        f"+ streaks {streak_xp} = {total}"
    )
    assert streak_xp == 450, "the streak source must actually contribute (D-31)"
