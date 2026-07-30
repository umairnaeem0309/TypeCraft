"""Classroom leaderboard (FR-110..FR-114, SR-006, ADR-011).

The defect this closes (D-10): `ProfileManager.create()` seeds a zero-valued
`lesson_progress` row, and the old query grouped over that table with no
completion filter — so **every** profile appeared on the board with a score of 0.
In a class of thirty, the ten slots were occupied by whoever was created first,
and a child who had never typed a word ranked alongside one who had.
"""

import pytest

from typecraft.models.attempt import AttemptStatus


def names(rows):
    return [r["name"] for r in rows]


def make_student(ctx, name):
    student = ctx.profiles.create(name, "avatar_fox")
    return student


# --------------------------------------------------------------------- exclusion rules

def test_a_profile_with_no_attempts_does_not_appear(app_ctx):
    """FR-112 — the D-10 regression test."""
    make_student(app_ctx, "Never Typed")

    assert app_ctx.progression.leaderboard("wpm") == []
    assert app_ctx.progression.leaderboard("accuracy") == []


def test_a_profile_with_only_incomplete_attempts_does_not_appear(app_ctx, attempt_factory):
    """FR-064/FR-112: abandoned attempts are recorded but never ranked."""
    student = make_student(app_ctx, "Gave Up")
    for _ in range(5):
        app_ctx.progression.score(
            attempt_factory(student.id, accuracy=100.0, wpm_net=99.0,
                            status=AttemptStatus.INCOMPLETE),
            student,
        )

    assert app_ctx.progression.leaderboard("wpm") == []


def test_a_completed_attempt_puts_a_student_on_the_board(app_ctx, attempt_factory):
    student = make_student(app_ctx, "Amina")
    app_ctx.progression.score(
        attempt_factory(student.id, accuracy=92.0, wpm_net=24.0), student)

    board = app_ctx.progression.leaderboard("wpm")
    assert len(board) == 1
    assert board[0]["name"] == "Amina"
    assert board[0]["score"] == pytest.approx(24.0)


def test_only_students_who_finished_something_are_listed(app_ctx, attempt_factory):
    """The whole point, stated as one scenario: a classroom where most children
    have not finished a lesson yet."""
    finished = make_student(app_ctx, "Finished")
    for name in ("Fresh A", "Fresh B", "Fresh C"):
        make_student(app_ctx, name)
    abandoned = make_student(app_ctx, "Abandoned")
    app_ctx.progression.score(
        attempt_factory(abandoned.id, status=AttemptStatus.INCOMPLETE), abandoned)
    app_ctx.progression.score(
        attempt_factory(finished.id, accuracy=90.0, wpm_net=18.0), finished)

    assert names(app_ctx.progression.leaderboard("wpm")) == ["Finished"]


def test_a_zero_score_is_not_listed_even_after_a_completion(app_ctx, attempt_factory):
    """A completed attempt at 0 wpm has nothing to rank on the speed board."""
    student = make_student(app_ctx, "Very Slow")
    app_ctx.progression.score(
        attempt_factory(student.id, accuracy=90.0, wpm_net=0.0), student)

    assert app_ctx.progression.leaderboard("wpm") == []
    # ...but their accuracy still counts on the accuracy board.
    assert names(app_ctx.progression.leaderboard("accuracy")) == ["Very Slow"]


# --------------------------------------------------------------------- ranking

def test_students_are_ordered_by_best_score_descending(app_ctx, attempt_factory):
    for name, wpm in (("Slow", 10.0), ("Fast", 30.0), ("Middle", 20.0)):
        student = make_student(app_ctx, name)
        app_ctx.progression.score(
            attempt_factory(student.id, accuracy=90.0, wpm_net=wpm), student)

    assert names(app_ctx.progression.leaderboard("wpm")) == ["Fast", "Middle", "Slow"]


def test_a_students_best_result_is_used_not_their_latest(app_ctx, attempt_factory):
    """FR-111: the board shows a personal best, so a bad day cannot cost a place."""
    student = make_student(app_ctx, "Amina")
    app_ctx.progression.score(
        attempt_factory(student.id, accuracy=98.0, wpm_net=35.0), student)
    app_ctx.progression.score(
        attempt_factory(student.id, accuracy=86.0, wpm_net=9.0), student)

    assert app_ctx.progression.leaderboard("wpm")[0]["score"] == pytest.approx(35.0)


def test_the_best_is_taken_across_lessons(app_ctx, attempt_factory):
    student = make_student(app_ctx, "Amina")
    app_ctx.progression.score(
        attempt_factory(student.id, "t1l1", accuracy=88.0, wpm_net=12.0), student)
    app_ctx.progression.score(
        attempt_factory(student.id, "t1l2", accuracy=99.0, wpm_net=28.0), student)

    assert app_ctx.progression.leaderboard("wpm")[0]["score"] == pytest.approx(28.0)
    assert app_ctx.progression.leaderboard("accuracy")[0]["score"] == pytest.approx(99.0)


def test_each_student_occupies_exactly_one_row(app_ctx, attempt_factory):
    """Grouping bug guard: eight completions must not become eight rows."""
    student = make_student(app_ctx, "Amina")
    for lesson_id in ("t1l1", "t1l2", "t1l3", "t1l4"):
        for _ in range(2):
            app_ctx.progression.score(
                attempt_factory(student.id, lesson_id, accuracy=90.0), student)

    assert len(app_ctx.progression.leaderboard("wpm")) == 1


def test_the_two_boards_rank_independently(app_ctx, attempt_factory):
    """FR-111: fast-and-sloppy tops one board, slow-and-careful the other."""
    fast = make_student(app_ctx, "Fast Sloppy")
    app_ctx.progression.score(
        attempt_factory(fast.id, accuracy=86.0, wpm_net=40.0), fast)
    careful = make_student(app_ctx, "Slow Careful")
    app_ctx.progression.score(
        attempt_factory(careful.id, accuracy=100.0, wpm_net=8.0), careful)

    assert names(app_ctx.progression.leaderboard("wpm"))[0] == "Fast Sloppy"
    assert names(app_ctx.progression.leaderboard("accuracy"))[0] == "Slow Careful"


def test_ties_are_broken_deterministically(app_ctx, attempt_factory):
    """FR-113. Identical scores must produce the same order every time, or the
    board reshuffles each time a child opens it."""
    for name in ("First Joined", "Second Joined", "Third Joined"):
        student = make_student(app_ctx, name)
        app_ctx.progression.score(
            attempt_factory(student.id, accuracy=95.0, wpm_net=20.0), student)

    expected = ["First Joined", "Second Joined", "Third Joined"]
    for _ in range(5):
        assert names(app_ctx.progression.leaderboard("wpm")) == expected


def test_the_board_is_capped(app_ctx, attempt_factory):
    for i in range(15):
        student = make_student(app_ctx, f"S{i:02d}")
        app_ctx.progression.score(
            attempt_factory(student.id, accuracy=90.0, wpm_net=float(i + 1)), student)

    assert len(app_ctx.progression.leaderboard("wpm")) == 10
    assert len(app_ctx.progression.leaderboard("wpm", limit=3)) == 3
    assert names(app_ctx.progression.leaderboard("wpm", limit=3)) == ["S14", "S13", "S12"]


def test_an_unknown_board_name_raises(app_ctx):
    """SR-006: the sort column comes from a fixed allow-list, never from input, so
    an unexpected key is a programmer error rather than a silent default or an
    injection point."""
    with pytest.raises(KeyError):
        app_ctx.progression.leaderboard("'; DROP TABLE profiles; --")


# --------------------------------------------------------------------- scene

def test_the_scene_renders_both_tabs(app_ctx, display, attempt_factory):
    from typecraft.scenes.leaderboard import LeaderboardScene

    student = make_student(app_ctx, "Amina")
    app_ctx.progression.score(
        attempt_factory(student.id, accuracy=93.0, wpm_net=21.0), student)

    scene = LeaderboardScene(app_ctx)
    scene.on_enter()
    assert names(scene.rows) == ["Amina"]
    scene.render(display)

    scene._set_tab("accuracy")
    assert names(scene.rows) == ["Amina"]
    scene.render(display)


def test_the_scene_shows_an_empty_state_when_nobody_qualifies(app_ctx, display):
    from typecraft.scenes.leaderboard import LeaderboardScene

    make_student(app_ctx, "Never Typed")
    scene = LeaderboardScene(app_ctx)
    scene.on_enter()

    assert scene.rows == []
    scene.render(display)   # FR-114: must not crash on an empty board
