"""The scoring formulas (FR-050..FR-057, blueprint 2.4).

Every number a student, teacher, or leaderboard ever sees comes out of these six
functions, so they are pinned exactly — including the three worked examples the
blueprint states, which are the only independent check that the XP formula was
transcribed correctly.
"""

import pytest

from typecraft.engine import metrics as m


# --------------------------------------------------------------------------- accuracy

def test_accuracy_zero_keystrokes_is_zero_not_a_crash():
    """FR-053: divide-by-zero must be impossible."""
    assert m.accuracy_pct(0, 0) == 0.0


@pytest.mark.parametrize("correct,total,expected", [
    (0, 10, 0.0),
    (8, 10, 80.0),
    (10, 10, 100.0),
    (1, 3, pytest.approx(33.3333, abs=1e-4)),
])
def test_accuracy_values(correct, total, expected):
    assert m.accuracy_pct(correct, total) == expected


@pytest.mark.parametrize("correct,total", [(0, 1), (1, 1), (7, 9), (250, 250), (1, 1000)])
def test_accuracy_stays_within_zero_and_one_hundred(correct, total):
    """FR-044. Holds for any correct <= total, which the engine guarantees."""
    assert 0.0 <= m.accuracy_pct(correct, total) <= 100.0


# --------------------------------------------------------------------------- WPM

@pytest.mark.parametrize("minutes", [0.0, -1.0, -0.0001])
def test_wpm_is_zero_for_zero_or_negative_duration(minutes):
    """FR-053: a lesson finished in no measurable time must not report infinity."""
    assert m.gross_wpm(100, minutes) == 0.0
    assert m.net_wpm(100, minutes) == 0.0


def test_wpm_uses_five_characters_per_word():
    """Blueprint 2.4: one word == 5 characters, so 250 keystrokes in 1 minute is 50 wpm."""
    assert m.gross_wpm(250, 1.0) == 50.0
    assert m.net_wpm(250, 1.0) == 50.0


def test_net_wpm_equals_gross_wpm_times_accuracy():
    """Blueprint 2.4 states this identity; it is what makes net_wpm intuitive
    ('type fast AND correctly') and identical across all three input modes."""
    total, correct, minutes = 200, 180, 2.0
    accuracy = m.accuracy_pct(correct, total)
    assert m.net_wpm(correct, minutes) == pytest.approx(
        m.gross_wpm(total, minutes) * accuracy / 100.0
    )


def test_net_wpm_never_exceeds_gross_wpm():
    for correct, total in [(0, 10), (5, 10), (10, 10)]:
        assert m.net_wpm(correct, 1.0) <= m.gross_wpm(total, 1.0)


# --------------------------------------------------------------------------- stars

@pytest.mark.parametrize("accuracy,stars", [
    (0.0, 0), (50.0, 0), (84.99, 0),          # below the D2 pass line
    (85.0, 1), (88.0, 1), (91.99, 1),
    (92.0, 2), (95.0, 2), (96.99, 2),
    (97.0, 3), (99.5, 3), (100.0, 3),
])
def test_stars_boundaries(accuracy, stars):
    """FR-054. The 85.0 boundary is the same line as the unlock rule (FR-061),
    so 84.99 scoring 0 stars is load-bearing, not cosmetic."""
    assert m.stars_for(accuracy) == stars


# --------------------------------------------------------------------------- XP

@pytest.mark.parametrize("accuracy,net_wpm,tier,stars,expected_xp", [
    (88.0, 18.0, 1, 1, 26),   # blueprint 2.4 worked example 1
    (94.0, 22.0, 3, 2, 45),   # blueprint 2.4 worked example 2
    (99.0, 40.0, 5, 3, 89),   # blueprint 2.4 worked example 3
])
def test_xp_matches_the_blueprint_worked_examples(accuracy, net_wpm, tier, stars, expected_xp):
    """FR-055. These three are the only externally-stated values for the XP
    formula, so they are the real check that it was transcribed correctly."""
    assert m.stars_for(accuracy) == stars, "worked example's own star count disagrees"
    assert m.xp_for(accuracy, net_wpm, stars, tier) == expected_xp


@pytest.mark.parametrize("accuracy,expected", [(0.0, 0), (50.0, 2), (80.0, 4), (84.99, 4)])
def test_failed_attempt_earns_only_participation_xp(accuracy, expected):
    """FR-055: below 85 % the award is round(5*accuracy/100), capped at 4, and
    ignores speed, stars, and tier entirely.

    50 % gives 2 rather than 3 because Python's round() is banker's rounding:
    round(2.5) == 2. Pinned deliberately so the behaviour is a decision on record
    rather than a surprise if the formula is ever revisited.
    """
    assert m.xp_for(accuracy, 40.0, 3, 5) == expected


def test_speed_bonus_is_capped_at_forty_wpm():
    """A very fast student must not earn unbounded XP."""
    at_cap = m.xp_for(100.0, 40.0, 3, 1)
    beyond = m.xp_for(100.0, 400.0, 3, 1)
    assert at_cap == beyond


def test_higher_tier_awards_more_xp_for_identical_performance():
    same = dict(accuracy=95.0, net_wpm_value=20.0, stars=2)
    assert m.xp_for(tier=5, **same) > m.xp_for(tier=1, **same)


def test_more_stars_award_more_xp_for_identical_accuracy_band():
    assert m.xp_for(97.0, 20.0, 3, 1) > m.xp_for(97.0, 20.0, 1, 1)


def test_xp_is_never_negative():
    for accuracy in (0.0, 42.0, 85.0, 100.0):
        assert m.xp_for(accuracy, 0.0, 0, 1) >= 0


# --------------------------------------------------------------------------- levels

#: Blueprint 2.4 level table: cumulative XP needed to *reach* each level.
LEVEL_TABLE = [(1, 0), (2, 50), (3, 150), (4, 300), (5, 500),
               (6, 750), (7, 1050), (8, 1400), (9, 1800), (10, 2250)]


@pytest.mark.parametrize("level,xp", LEVEL_TABLE)
def test_xp_to_reach_matches_the_blueprint_table(level, xp):
    assert m.xp_to_reach(level) == xp


@pytest.mark.parametrize("level,xp", LEVEL_TABLE)
def test_exactly_enough_xp_reaches_that_level(level, xp):
    assert m.level_for(xp) == level


@pytest.mark.parametrize("level,xp", LEVEL_TABLE[1:])
def test_one_xp_short_stays_on_the_previous_level(level, xp):
    assert m.level_for(xp - 1) == level - 1


def test_level_is_capped_at_ten():
    """FR-056. Level 10 is the top of the curve; more XP must not invent level 11."""
    assert m.level_for(2250) == 10
    assert m.level_for(999_999) == 10


def test_level_floor_is_one():
    assert m.level_for(0) == 1
    assert m.level_for(-5) == 1


# --------------------------------------------------------------------------- streak bonus

@pytest.mark.parametrize("streak,bonus", [(0, 0), (1, 5), (3, 15), (5, 25), (6, 25), (365, 25)])
def test_daily_streak_bonus_saturates_at_five_days(streak, bonus):
    """FR-057: +5 per day, capped at 5 days, so the bonus stays a nudge rather
    than the dominant XP source."""
    assert m.daily_streak_bonus(streak) == bonus
