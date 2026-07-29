"""Badge catalogue, criteria, and award idempotency (FR-080..FR-083).

Badge *text* is teacher-editable JSON; badge *criteria* are code. These tests
cover the criteria and the award mechanics — a badge granted twice would pay its
XP bonus twice, which is the failure mode that matters.
"""

import pytest

from typecraft.models.attempt import AttemptStatus

EXPECTED_CODES = {
    "first_steps", "home_row_hero", "sharp_shooter", "speed_demon", "combo_king",
    "perfect_week", "triple_star", "rising_star", "keyboard_master", "marathon",
}


def _earned(ctx, profile_id):
    return {r["code"] for r in ctx.db.query(
        """SELECT b.code FROM profile_badges pb JOIN badges b ON b.id = pb.badge_id
           WHERE pb.profile_id=?""",
        (profile_id,),
    )}


# --------------------------------------------------------------------- catalogue

def test_ten_badges_are_synced_from_json(app_ctx):
    """FR-080."""
    codes = {r["code"] for r in app_ctx.db.query("SELECT code FROM badges")}
    assert codes == EXPECTED_CODES


def test_every_badge_has_display_text_and_a_bonus(app_ctx):
    for row in app_ctx.db.query("SELECT * FROM badges"):
        assert row["name"].strip()
        assert row["description"].strip()
        assert row["xp_bonus"] > 0


def test_catalogue_sync_does_not_duplicate_on_reconstruction(app_ctx, writable_dir):
    """BadgeManager runs its sync in the constructor, and AppContext is built on
    every launch. A second launch must not insert eleven more rows."""
    from typecraft.managers.badge_manager import BadgeManager

    before = app_ctx.db.query("SELECT COUNT(*) AS c FROM badges")[0]["c"]
    BadgeManager(app_ctx.db, app_ctx.lessons)
    BadgeManager(app_ctx.db, app_ctx.lessons)
    assert app_ctx.db.query("SELECT COUNT(*) AS c FROM badges")[0]["c"] == before


# --------------------------------------------------------------------- criteria

def test_first_lesson_earns_first_steps(profile, attempt_factory):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=90.0), student)
    assert "first_steps" in _earned(ctx, student.id)


def test_perfect_accuracy_earns_sharp_shooter(profile, attempt_factory):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=100.0), student)
    assert "sharp_shooter" in _earned(ctx, student.id)


def test_ninety_nine_percent_does_not_earn_sharp_shooter(profile, attempt_factory):
    """The criterion is 100 %, so it must not be reachable at 99 %."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=99.0), student)
    assert "sharp_shooter" not in _earned(ctx, student.id)


@pytest.mark.parametrize("wpm,expected", [(29.0, False), (30.0, True)])
def test_speed_demon_needs_thirty_net_wpm(profile, attempt_factory, wpm, expected):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=95.0, wpm_net=wpm), student)
    assert ("speed_demon" in _earned(ctx, student.id)) is expected


@pytest.mark.parametrize("combo,expected", [(49, False), (50, True)])
def test_combo_king_needs_a_fifty_keystroke_combo(profile, attempt_factory, combo, expected):
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=95.0, max_combo=combo), student)
    assert ("combo_king" in _earned(ctx, student.id)) is expected


def test_home_row_hero_needs_every_tier_one_lesson(profile, attempt_factory):
    """FR-081: a partial tier must not earn it."""
    ctx, student = profile
    tier1 = [l for l in ctx.lessons._ordered if l.tier == 1]

    for lesson in tier1[:-1]:
        ctx.progression.score(attempt_factory(student.id, lesson.id, accuracy=95.0), student)
    assert "home_row_hero" not in _earned(ctx, student.id)

    ctx.progression.score(attempt_factory(student.id, tier1[-1].id, accuracy=95.0), student)
    assert "home_row_hero" in _earned(ctx, student.id)


def test_triple_star_needs_three_stars_on_five_different_lessons(profile, attempt_factory):
    ctx, student = profile
    lessons = ctx.lessons._ordered[:5]

    for lesson in lessons[:4]:
        ctx.progression.score(attempt_factory(student.id, lesson.id, accuracy=99.0), student)
    assert "triple_star" not in _earned(ctx, student.id)

    ctx.progression.score(attempt_factory(student.id, lessons[4].id, accuracy=99.0), student)
    assert "triple_star" in _earned(ctx, student.id)


def test_repeating_one_lesson_does_not_earn_triple_star(profile, attempt_factory):
    """The criterion counts distinct lessons, so grinding lesson 1 five times must
    not qualify. lesson_progress is keyed per lesson, which is what enforces it."""
    ctx, student = profile
    for _ in range(6):
        ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=99.0), student)
    assert "triple_star" not in _earned(ctx, student.id)


def test_incomplete_attempts_earn_no_badges(profile, attempt_factory):
    """FR-075."""
    ctx, student = profile
    for _ in range(30):
        ctx.progression.score(
            attempt_factory(student.id, accuracy=100.0, wpm_net=60.0, max_combo=99,
                            status=AttemptStatus.INCOMPLETE),
            student,
        )
    assert _earned(ctx, student.id) == set()


# --------------------------------------------------------------------- idempotency

def test_a_badge_is_awarded_at_most_once(profile, attempt_factory):
    """FR-082. The XP bonus is applied at award time, so a repeat award would pay
    twice — the reason this is the most important badge test."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, accuracy=100.0), student)
    xp_after_first = ctx.db.query(
        "SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"]

    for _ in range(5):
        ctx.progression.score(attempt_factory(student.id, accuracy=100.0), student)

    rows = ctx.db.query(
        """SELECT b.code, COUNT(*) AS c FROM profile_badges pb
           JOIN badges b ON b.id = pb.badge_id WHERE pb.profile_id=? GROUP BY b.code""",
        (student.id,),
    )
    assert all(r["c"] == 1 for r in rows), f"duplicate awards: {rows}"

    # XP grew only by the five later attempts' own awards, not by re-paid bonuses.
    expected = xp_after_first + 5 * attempt_factory(student.id, accuracy=100.0).xp_awarded
    assert ctx.db.query(
        "SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"] == expected


def test_evaluate_returns_only_newly_awarded_codes(profile, attempt_factory):
    """The results screen shows "new badge!" from this return value, so a repeat
    must come back empty rather than re-announcing."""
    ctx, student = profile
    attempt = attempt_factory(student.id, accuracy=100.0)

    ctx.progression.score(attempt, student)
    first_round = ctx.badges.evaluate(student, attempt)

    assert first_round == [], "already awarded during score(); nothing new to report"

    fresh = ctx.badges.evaluate(student, attempt)
    assert fresh == []


def test_badge_bonus_xp_is_persisted(profile, attempt_factory):
    """FR-083 (the XP half — the level half is defect D-11, see test_progression)."""
    ctx, student = profile
    attempt = attempt_factory(student.id, accuracy=90.0)

    ctx.progression.score(attempt, student)

    from typecraft.engine import metrics as m

    stored = ctx.db.query(
        "SELECT total_xp FROM profiles WHERE id=?", (student.id,))[0]["total_xp"]
    assert stored == attempt.xp_awarded + 25 + m.daily_streak_bonus(1)
