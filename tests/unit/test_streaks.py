"""The daily-streak state machine (FR-086, FR-087, blueprint decision D4).

`today` is injected rather than read from the clock, so every branch is testable
without touching the system date. StreakManager needs no database for `touch()`.

The clock-rollback branch is the one that matters in the field: school PCs have
wrong clocks, and a child must never lose a streak they earned because the date
appeared to go backwards.
"""

import pytest

from typecraft.managers.streak_manager import StreakManager
from typecraft.models.profile import Profile


@pytest.fixture
def streaks():
    return StreakManager(db=None)  # touch() is pure; no database involved


def make_profile(**kwargs):
    defaults = dict(id=1, name="Amina", avatar_key="avatar_fox",
                    current_streak=0, longest_streak=0, last_active_date="")
    defaults.update(kwargs)
    return Profile(**defaults)


def test_first_ever_completion_starts_a_one_day_streak(streaks):
    """FR-086."""
    student = make_profile(last_active_date="")
    streaks.touch(student, "2026-07-29")

    assert student.current_streak == 1
    assert student.longest_streak == 1
    assert student.last_active_date == "2026-07-29"


def test_none_last_active_date_is_treated_as_never_active(streaks):
    """A fresh profile row has SQL NULL here, which arrives as None."""
    student = make_profile(last_active_date=None)
    streaks.touch(student, "2026-07-29")
    assert student.current_streak == 1


def test_a_second_lesson_the_same_day_does_not_increment(streaks):
    """FR-086: the streak counts days, not lessons."""
    student = make_profile(current_streak=3, longest_streak=5, last_active_date="2026-07-29")

    for _ in range(4):
        streaks.touch(student, "2026-07-29")

    assert student.current_streak == 3
    assert student.longest_streak == 5


def test_the_next_day_increments(streaks):
    student = make_profile(current_streak=3, longest_streak=3, last_active_date="2026-07-29")
    streaks.touch(student, "2026-07-30")

    assert student.current_streak == 4
    assert student.longest_streak == 4


def test_a_missed_day_restarts_at_one(streaks):
    student = make_profile(current_streak=6, longest_streak=6, last_active_date="2026-07-29")
    streaks.touch(student, "2026-07-31")   # one day skipped

    assert student.current_streak == 1
    assert student.longest_streak == 6, "the record must survive the reset"


def test_a_long_absence_restarts_at_one(streaks):
    student = make_profile(current_streak=10, longest_streak=10, last_active_date="2026-01-01")
    streaks.touch(student, "2026-07-29")

    assert student.current_streak == 1
    assert student.longest_streak == 10


def test_a_backwards_clock_never_punishes_the_student(streaks):
    """FR-086 and AS-02. On a shared school PC the clock can be wrong; the streak
    must be left alone rather than reset."""
    student = make_profile(current_streak=7, longest_streak=7, last_active_date="2026-07-29")
    streaks.touch(student, "2026-07-20")   # clock jumped nine days back

    assert student.current_streak == 7
    assert student.longest_streak == 7


def test_a_backwards_clock_does_not_rewrite_the_last_active_date_forward(streaks):
    """After a rollback the stored date does move to `today`, which means the next
    genuine day counts as +1 from there. Pinned as the documented consequence of
    the guard so a future change is a deliberate one."""
    student = make_profile(current_streak=7, longest_streak=7, last_active_date="2026-07-29")
    streaks.touch(student, "2026-07-20")
    assert student.last_active_date == "2026-07-20"

    streaks.touch(student, "2026-07-21")
    assert student.current_streak == 8


def test_month_and_year_boundaries_are_handled_as_real_dates(streaks):
    """String comparison would get these wrong; date arithmetic gets them right."""
    student = make_profile(current_streak=2, longest_streak=2, last_active_date="2026-07-31")
    streaks.touch(student, "2026-08-01")
    assert student.current_streak == 3

    student = make_profile(current_streak=4, longest_streak=4, last_active_date="2026-12-31")
    streaks.touch(student, "2027-01-01")
    assert student.current_streak == 5


def test_a_leap_day_boundary_increments(streaks):
    student = make_profile(current_streak=1, longest_streak=1, last_active_date="2028-02-28")
    streaks.touch(student, "2028-02-29")
    assert student.current_streak == 2


def test_a_seven_day_run_reaches_the_perfect_week_threshold(streaks):
    """The `perfect_week` badge criterion is current_streak >= 7, so the machine
    must actually be able to get there."""
    student = make_profile(last_active_date="")
    for day in range(1, 8):
        streaks.touch(student, f"2026-07-{day:02d}")

    assert student.current_streak == 7
    assert student.longest_streak == 7


def test_longest_streak_is_a_high_water_mark(streaks):
    student = make_profile(last_active_date="")
    for day in range(1, 5):                      # four consecutive days
        streaks.touch(student, f"2026-07-{day:02d}")
    assert (student.current_streak, student.longest_streak) == (4, 4)

    streaks.touch(student, "2026-07-20")         # long gap
    assert (student.current_streak, student.longest_streak) == (1, 4)

    streaks.touch(student, "2026-07-21")
    assert (student.current_streak, student.longest_streak) == (2, 4)
