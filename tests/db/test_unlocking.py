"""Lesson ordering and the 85 % unlock gate (FR-020..FR-027, FR-060..FR-066).

Decision D2: accuracy >= 85 % on a *completed* attempt unlocks the next lesson in
tier/order sequence. WPM never gates progress. The 85.0 boundary is exact — a
child on 84.99 % stays where they are, so the comparison must not be softened.
"""

import pytest

from typecraft.managers.lesson_manager import UNLOCK_ACCURACY_THRESHOLD
from typecraft.models.attempt import AttemptStatus


def test_twenty_lessons_load_in_five_tiers(app_ctx):
    """FR-021."""
    assert len(app_ctx.lessons.tiers()) == 5
    assert len(app_ctx.lessons._ordered) >= 20


def test_lessons_are_ordered_by_tier_then_order(app_ctx):
    """FR-060: this flat sequence *is* the unlock chain, so its order matters."""
    lessons = app_ctx.lessons._ordered
    tiers = [l.tier for l in lessons]
    assert tiers == sorted(tiers), "tiers are interleaved"
    for tier in range(1, 6):
        orders = [l.order for l in lessons if l.tier == tier]
        assert orders == sorted(orders), f"tier {tier} lessons out of order"


def test_lesson_ids_are_unique(app_ctx):
    """FR-022/DR-005: the id is a database key; a duplicate would merge two
    lessons' history."""
    ids = [l.id for l in app_ctx.lessons._ordered]
    assert len(ids) == len(set(ids))


def test_next_lesson_id_walks_the_chain(app_ctx):
    lessons = app_ctx.lessons._ordered
    for current, following in zip(lessons, lessons[1:]):
        assert app_ctx.lessons.next_lesson_id(current.id) == following.id


def test_the_final_lesson_has_no_successor(app_ctx):
    """FR-066: unlocking past the end is a no-op, not an error."""
    last = app_ctx.lessons._ordered[-1]
    assert app_ctx.lessons.next_lesson_id(last.id) is None


def test_every_lesson_has_typable_content(app_ctx):
    """FR-025: the joined target must be non-empty, or the engine finishes the
    lesson before the student presses a key."""
    for lesson in app_ctx.lessons._ordered:
        assert lesson.target_text().strip(), f"{lesson.id} has no content"
        assert lesson.default_mode in {"lock_on_error", "backspace", "free_advance"}


# --------------------------------------------------------------------- the 85 % gate

@pytest.mark.parametrize("accuracy,should_unlock", [
    (0.0, False),
    (84.99, False),
    (UNLOCK_ACCURACY_THRESHOLD, True),   # exactly 85.0
    (85.01, True),
    (100.0, True),
])
def test_unlock_threshold_is_exact(profile, attempt_factory, accuracy, should_unlock):
    """FR-061. 84.99 must not round up to a pass."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=accuracy), student)

    assert ctx.lessons.is_unlocked(student, "t1l2") is should_unlock


def test_wpm_never_gates_unlocking(profile, attempt_factory):
    """FR-062: a slow but accurate child progresses."""
    ctx, student = profile
    ctx.progression.score(
        attempt_factory(student.id, "t1l1", accuracy=99.0, wpm_net=1.0), student)

    assert ctx.lessons.is_unlocked(student, "t1l2") is True


def test_an_incomplete_attempt_never_unlocks(profile, attempt_factory):
    """FR-064: only completed attempts count, however accurate the fragment was."""
    ctx, student = profile
    ctx.progression.score(
        attempt_factory(student.id, "t1l1", accuracy=100.0, status=AttemptStatus.INCOMPLETE),
        student,
    )

    assert ctx.lessons.is_unlocked(student, "t1l2") is False


def test_unlocking_is_idempotent(profile, attempt_factory):
    """FR-063: unlimited retries; passing twice must not duplicate a progress row."""
    ctx, student = profile
    for _ in range(3):
        ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=95.0), student)

    rows = ctx.db.query(
        "SELECT COUNT(*) AS c FROM lesson_progress WHERE profile_id=? AND lesson_id='t1l2'",
        (student.id,),
    )
    assert rows[0]["c"] == 1
    assert ctx.lessons.is_unlocked(student, "t1l2") is True


def test_a_later_failure_does_not_relock_the_next_lesson(profile, attempt_factory):
    """FR-063: progress is never taken away."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=95.0), student)
    ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=20.0), student)

    assert ctx.lessons.is_unlocked(student, "t1l2") is True


def test_unlocking_advances_only_one_step(profile, attempt_factory):
    """FR-060: passing lesson 1 must not open lesson 3."""
    ctx, student = profile
    ctx.progression.score(attempt_factory(student.id, "t1l1", accuracy=95.0), student)

    assert ctx.lessons.is_unlocked(student, "t1l2") is True
    assert ctx.lessons.is_unlocked(student, "t1l3") is False


def test_unlocking_crosses_a_tier_boundary(profile, attempt_factory):
    """The chain is global, not per-tier: finishing the last Tier 1 lesson opens
    the first Tier 2 lesson."""
    ctx, student = profile
    tier1 = [l for l in ctx.lessons._ordered if l.tier == 1]
    last_of_tier1 = tier1[-1]
    first_of_tier2 = next(l for l in ctx.lessons._ordered if l.tier == 2)

    ctx.progression.score(
        attempt_factory(student.id, last_of_tier1.id, accuracy=95.0), student)

    assert ctx.lessons.is_unlocked(student, first_of_tier2.id) is True


def test_completing_the_final_lesson_scores_normally_and_unlocks_nothing(
        profile, attempt_factory):
    """FR-066: there is no lesson 21, so the unlock step must be a quiet no-op
    while the attempt itself still scores."""
    ctx, student = profile
    last = ctx.lessons._ordered[-1]

    ctx.progression.score(attempt_factory(student.id, last.id, accuracy=100.0, tier=5), student)

    assert ctx.db.query(
        "SELECT COUNT(*) AS c FROM lesson_attempts WHERE lesson_id=? AND status='complete'",
        (last.id,),
    )[0]["c"] == 1
    unlocked = {r["lesson_id"] for r in ctx.db.query(
        "SELECT lesson_id FROM lesson_progress WHERE profile_id=? AND is_unlocked=1",
        (student.id,),
    )}
    known = {l.id for l in ctx.lessons._ordered}
    # Lesson 1 from profile creation, plus the final lesson itself: the progress
    # cache marks a lesson unlocked when it records a completion there, which is
    # sound (you cannot complete a locked lesson through the UI).
    assert unlocked == {ctx.lessons.first_lesson().id, last.id}
    assert unlocked <= known, f"unlocked a lesson that does not exist: {unlocked - known}"
