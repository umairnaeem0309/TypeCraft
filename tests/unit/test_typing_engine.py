"""TypingEngine bookkeeping (FR-040..FR-048).

Characterisation tests written *before* the fix, per TC-005. Everything marked
`xfail(strict=True)` is a defect reproduction, not an aspiration: the assertion
states what TC-006 must make true, and `strict` means the suite goes red the
moment the behaviour is fixed, forcing the marker to be removed. Nothing here is
allowed to be "fixed" by weakening an assertion.

The accounting policy asserted is the OQ-001 resolution (REQUIREMENTS.md 13):
Backspace moves the cursor and clears the on-screen status only. It never edits
total_keystrokes, errors, or correct_keystrokes, so every character-producing
keystroke posts exactly one ledger entry that is never reversed. A corrected
mistake still counts against accuracy; a separate non-scoring `corrections_made`
counter gives the student credit for noticing.
"""

import pytest

from typecraft.engine.input_modes import create_mode
from typecraft.engine.typing_engine import TypingEngine
from typecraft.models.attempt import AttemptStatus, CharStatus


class FakeClock:
    """Monotonic clock under test control, so WPM is exact and nothing sleeps."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make_engine(target="abc", mode_key="lock_on_error", tier=1, clock=None):
    clock = clock if clock is not None else FakeClock()
    engine = TypingEngine(
        target=target, mode=create_mode(mode_key), profile_id=1, lesson_id="t1l1",
        mode_key=mode_key, tier=tier, clock=clock,
    )
    return engine, clock


def type_all(engine, text):
    for ch in text:
        engine.feed_key(ch)


def assert_ledger_consistent(engine, note=""):
    """FR-043/FR-044/FR-045, the three invariants that make every stored metric
    trustworthy."""
    assert engine.correct_keystrokes + engine.errors == engine.total_keystrokes, (
        f"ledger broken{note}: correct={engine.correct_keystrokes} + "
        f"errors={engine.errors} != total={engine.total_keystrokes}"
    )
    assert engine.correct_keystrokes <= engine.total_keystrokes, f"correct > total{note}"
    assert engine.correct_keystrokes >= 0 and engine.errors >= 0, f"negative counter{note}"
    assert 0.0 <= engine.metrics()["accuracy"] <= 100.0, f"accuracy out of range{note}"


# --------------------------------------------------------------------------- initial state

def test_fresh_engine_is_zeroed_and_pending():
    engine, _ = make_engine("abc")
    assert engine.cursor == 0
    assert engine.char_status == [CharStatus.PENDING] * 3
    assert (engine.total_keystrokes, engine.errors, engine.correct_keystrokes) == (0, 0, 0)
    assert (engine.combo, engine.max_combo) == (0, 0)
    assert engine.is_finished() is False


def test_untouched_engine_reports_zero_metrics_not_an_error():
    """FR-053: a student who opens a lesson and walks away must not crash it."""
    engine, _ = make_engine("abc")
    stats = engine.metrics()
    assert stats["accuracy"] == 0.0
    assert stats["wpm_net"] == 0.0
    assert stats["wpm_gross"] == 0.0
    assert stats["elapsed_sec"] == 0.0


def test_clock_does_not_start_until_the_first_keystroke():
    """FR-041: timing runs from the first keypress, not from scene entry, so
    reading the instructions does not damage the student's WPM."""
    engine, clock = make_engine("abc")
    clock.advance(600)  # ten minutes of staring at the screen
    assert engine.metrics()["elapsed_sec"] == 0.0

    engine.feed_key("a")
    clock.advance(60)
    assert engine.metrics()["elapsed_sec"] == pytest.approx(60.0)


# --------------------------------------------------------------------------- clean runs

@pytest.mark.parametrize("mode_key", ["lock_on_error", "backspace", "free_advance"])
def test_perfect_run_in_every_mode(mode_key):
    engine, _ = make_engine("fj fj", mode_key)
    type_all(engine, "fj fj")

    assert engine.is_finished() is True
    assert engine.total_keystrokes == 5
    assert engine.correct_keystrokes == 5
    assert engine.errors == 0
    assert engine.metrics()["accuracy"] == 100.0
    assert engine.max_combo == 5
    assert engine.char_status == [CharStatus.CORRECT] * 5
    assert_ledger_consistent(engine)


def test_wpm_is_computed_from_the_injected_clock():
    """25 keystrokes in exactly one minute is 5 wpm at 5 characters per word."""
    target = "a" * 25
    engine, clock = make_engine(target, "free_advance")
    type_all(engine, target[:-1])
    clock.advance(60)
    engine.feed_key(target[-1])

    stats = engine.metrics()
    assert stats["wpm_gross"] == pytest.approx(5.0)
    assert stats["wpm_net"] == pytest.approx(5.0)


def test_instant_completion_reports_zero_wpm_not_infinity():
    """FR-053: a zero-duration attempt (or a very fast paste) must be safe."""
    engine, _ = make_engine("abc", "free_advance")  # clock never advances
    type_all(engine, "abc")
    stats = engine.metrics()
    assert stats["wpm_gross"] == 0.0
    assert stats["wpm_net"] == 0.0
    assert stats["accuracy"] == 100.0


# --------------------------------------------------------------------------- combo

def test_combo_breaks_on_error_and_max_combo_is_retained():
    """FR-048."""
    engine, _ = make_engine("abcdef", "free_advance")
    type_all(engine, "abc")
    assert (engine.combo, engine.max_combo) == (3, 3)

    engine.feed_key("z")  # wrong at index 3
    assert engine.combo == 0
    assert engine.max_combo == 3

    engine.feed_key("e")
    assert (engine.combo, engine.max_combo) == (1, 3)


# --------------------------------------------------------------------------- backspace permission

@pytest.mark.parametrize("mode_key", ["lock_on_error", "free_advance"])
def test_backspace_is_completely_inert_in_the_other_two_modes(mode_key):
    """FR-032/FR-034: no cursor movement and no counter movement."""
    engine, _ = make_engine("abc", mode_key)
    type_all(engine, "ab")
    before = (engine.cursor, engine.total_keystrokes, engine.errors, engine.correct_keystrokes)

    for _ in range(5):
        engine.feed_key("\b")

    after = (engine.cursor, engine.total_keystrokes, engine.errors, engine.correct_keystrokes)
    assert after == before
    assert_ledger_consistent(engine)


def test_backspace_is_never_counted_as_a_keystroke_in_backspace_mode():
    """FR-042: Backspace is not a character-producing key, so it must not appear
    in total_keystrokes in any mode -- including the one that allows it."""
    engine, _ = make_engine("abc", "backspace")
    type_all(engine, "ab")
    before_total = engine.total_keystrokes

    engine.feed_key("\b")

    assert engine.total_keystrokes == before_total
    assert engine.cursor == 1


def test_lock_on_error_holds_the_cursor_until_the_right_key_arrives():
    """FR-032."""
    engine, _ = make_engine("abc")
    for wrong in "zzz":
        engine.feed_key(wrong)
        assert engine.cursor == 0

    engine.feed_key("a")
    assert engine.cursor == 1


# --------------------------------------------------------------------------- result()

def test_result_infers_complete_when_the_text_is_finished():
    engine, clock = make_engine("ab", "free_advance")
    type_all(engine, "a")
    clock.advance(30)
    engine.feed_key("b")

    result = engine.result()
    assert result.status is AttemptStatus.COMPLETE
    assert result.stars == 3          # 100% accuracy
    assert result.xp_awarded > 0
    assert result.completed_at != ""
    assert result.duration_sec == pytest.approx(30.0)


def test_result_infers_incomplete_when_abandoned_mid_lesson():
    engine, _ = make_engine("abcdef", "free_advance")
    type_all(engine, "abc")

    result = engine.result()
    assert result.status is AttemptStatus.INCOMPLETE


def test_incomplete_result_awards_no_stars_and_no_xp():
    """FR-076: an abandoned attempt must not feed progression."""
    engine, _ = make_engine("ab", "free_advance")
    type_all(engine, "ab")  # actually finished...

    result = engine.result(status=AttemptStatus.INCOMPLETE)  # ...but forced incomplete
    assert result.stars == 0
    assert result.xp_awarded == 0
    assert result.completed_at == ""


def test_result_char_statuses_is_a_snapshot_not_the_live_list():
    """The results screen must not mutate under it if the engine is touched again."""
    engine, _ = make_engine("abc", "free_advance")
    type_all(engine, "a")
    snapshot = engine.result().char_statuses

    engine.feed_key("b")
    assert snapshot[1] is CharStatus.PENDING


def test_result_carries_the_keystroke_counts_the_schema_needs():
    """FR-050/DR-003: these are stored per attempt, so the engine must expose them."""
    engine, _ = make_engine("abc", "free_advance")
    type_all(engine, "azc")

    result = engine.result()
    assert result.total_keystrokes == 3
    assert result.correct_keystrokes == 2
    assert result.errors == 1


# =========================================================================== DEFECTS
# Each test below reproduces a confirmed defect. strict=True means the suite fails
# if one starts passing, which forces the marker to be removed in TC-006.

@pytest.mark.xfail(strict=True, reason="defect D-08: _error_counted suppresses repeat "
                                      "errors, so correct + errors != total")
def test_D08_repeated_wrong_key_keeps_the_ledger_consistent():
    """FR-043. Three wrong keys then the right one at the same position is four
    real keystrokes: 3 errors + 1 correct. The `_error_counted` guard records
    only the first error while still counting all four keystrokes."""
    engine, _ = make_engine("ab")
    type_all(engine, "zzz")
    engine.feed_key("a")

    assert engine.total_keystrokes == 4
    assert engine.errors == 3
    assert engine.correct_keystrokes == 1
    assert_ledger_consistent(engine)


@pytest.mark.xfail(strict=True, reason="defect D-08: mistake count understates reality")
def test_D08_every_wrong_keystroke_counts_as_a_mistake():
    """The HUD's 'Mistakes' figure and the stored `errors` column must reflect
    what the student actually did, or the teacher's dashboard is misleading."""
    engine, _ = make_engine("ab")
    type_all(engine, "zzzzz")
    assert engine.errors == 5


@pytest.mark.xfail(strict=True, reason="defect D-07: correction erases the error and "
                                      "double-credits correct_keystrokes")
def test_D07_corrected_error_still_counts_against_accuracy():
    """OQ-001. Wrong key, Backspace, right key = 2 keystrokes, 1 error = 50%.
    The current code reports 100% with 0 mistakes, so a student who corrects
    everything scores identically to one who never erred."""
    engine, _ = make_engine("ab", "backspace")
    engine.feed_key("z")   # wrong at 0
    engine.feed_key("\b")  # revisit it
    engine.feed_key("a")   # correct it

    assert engine.total_keystrokes == 2
    assert engine.errors == 1
    assert engine.correct_keystrokes == 1
    assert engine.metrics()["accuracy"] == pytest.approx(50.0)


@pytest.mark.xfail(strict=True, reason="defect D-07: backspace credits a keystroke that "
                                      "was never pressed")
def test_D07_backspace_alone_cannot_manufacture_accuracy():
    """After one wrong key and one Backspace the student has typed exactly one
    character and got it wrong: 0% accuracy. The current code reports 100%
    before the replacement character is even typed."""
    engine, _ = make_engine("ab", "backspace")
    engine.feed_key("z")
    engine.feed_key("\b")

    assert engine.total_keystrokes == 1
    assert engine.errors == 1
    assert engine.correct_keystrokes == 0
    assert engine.metrics()["accuracy"] == 0.0


@pytest.mark.xfail(strict=True, reason="defect D-07: retyping over a backspaced correct "
                                      "character double-credits it")
def test_D07_navigating_back_over_a_correct_character_does_not_inflate_accuracy():
    """'a', wrong 'z', Backspace, Backspace, 'a', 'b' is 4 keystrokes with 1
    error = 75%. The current code erases the error and reports 100%."""
    engine, _ = make_engine("ab", "backspace")
    engine.feed_key("a")   # correct at 0
    engine.feed_key("z")   # wrong at 1
    engine.feed_key("\b")  # back over the error
    engine.feed_key("\b")  # back over the correct 'a'
    engine.feed_key("a")
    engine.feed_key("b")

    assert engine.total_keystrokes == 4
    assert engine.errors == 1
    assert engine.metrics()["accuracy"] == pytest.approx(75.0)
    assert_ledger_consistent(engine)


@pytest.mark.xfail(strict=True, reason="defect D-30: Backspace at cursor 0 in "
                                      "BackspaceMode is scored as a correct keystroke")
def test_D30_backspace_at_the_start_cannot_be_farmed_for_accuracy():
    """BackspaceMode.resolve() returns is_backspace=False when the cursor is at 0,
    so feed_key() falls through to the normal path and counts the Backspace as a
    correct keystroke. Pressing Backspace 20 times before typing anything banks
    20 free correct keystrokes and guarantees a pass."""
    engine, _ = make_engine("ab", "backspace")
    for _ in range(20):
        engine.feed_key("\b")

    assert engine.total_keystrokes == 0
    assert engine.correct_keystrokes == 0
    assert engine.combo == 0
    assert engine.metrics()["accuracy"] == 0.0


@pytest.mark.xfail(strict=True, reason="defect D-29: input after completion raises "
                                      "IndexError instead of being ignored")
def test_D29_input_after_completion_is_ignored():
    """FR-047, and the engine's own docstring says 'already finished, ignore
    stray input' -- but mode.resolve() reads target[cursor] before feed_key's
    guard is reached, so it raises."""
    engine, _ = make_engine("ab", "free_advance")
    type_all(engine, "ab")
    assert engine.is_finished()

    engine.feed_key("x")  # currently IndexError

    assert engine.total_keystrokes == 2
    assert engine.cursor == 2
