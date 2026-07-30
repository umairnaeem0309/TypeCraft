"""Randomised proof of the keystroke-ledger invariants (FR-043, FR-044, FR-045).

Hand-written cases catch the defects you thought of. These catch the ones you did
not. Every metric a student, teacher, or leaderboard sees is derived from three
counters, so if those can drift apart under *any* sequence of keys a child could
physically produce, every stored score is suspect.

The invariants, checked after *every* keystroke rather than only at the end:

    correct_keystrokes + errors == total_keystrokes     (FR-043)
    0 <= accuracy <= 100                                (FR-044)
    0 <= correct_keystrokes <= total_keystrokes         (FR-045)
    no counter is ever negative                         (FR-045)

**A finding worth keeping, established by these tests in TC-005.** The ledger
equation is necessary but *not sufficient*. Of the three accounting defects, only
D-08 actually broke FR-043, and only in `lock_on_error` — the one mode where the
cursor can revisit a position:

  - D-08 counted a repeated wrong key in total_keystrokes but suppressed the
    error, so the two sides genuinely diverged. Caught here.
  - D-07 decremented `errors` while incrementing `correct_keystrokes`, so the sum
    still matched total. The equation held; the values were wrong.
  - D-30 incremented total *and* correct together, so again the sum matched.

A randomised equation check therefore could not find D-07 or D-30. That is why
the scenarios in `test_typing_engine.py` assert exact expected counter values and
not merely the invariant — worth remembering before trusting a property test to
prove a fix.
"""

import random

import pytest

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
    HAS_HYPOTHESIS = True
except ImportError:  # pragma: no cover - hypothesis is a declared dev dependency
    HAS_HYPOTHESIS = False

from tests.unit.test_typing_engine import make_engine

MODES = ["lock_on_error", "backspace", "free_advance"]

TARGET = "asdf jkl; a sad lad"

#: Keys a child can actually produce at a TypeCraft lesson: the expected
#: characters, plausible wrong letters, space, and Backspace.
KEYPOOL = list("asdfjkl; ") + list("qwerty") + ["\b"] * 3

SEQUENCES_PER_MODE = 400
KEYS_PER_SEQUENCE = 40
SEED = 20260729  # fixed so a failure is always reproducible


def check_invariants(engine, mode_key, keys_fed):
    """Return a description of the first invariant broken, or None."""
    total = engine.total_keystrokes
    correct = engine.correct_keystrokes
    errors = engine.errors
    accuracy = engine.metrics()["accuracy"]
    context = f"mode={mode_key} keys={keys_fed!r} total={total} correct={correct} errors={errors}"

    if correct + errors != total:
        return f"FR-043 correct+errors != total :: {context}"
    if not 0.0 <= accuracy <= 100.0:
        return f"FR-044 accuracy={accuracy} out of range :: {context}"
    if correct > total:
        return f"FR-045 correct > total :: {context}"
    if min(total, correct, errors, engine.combo, engine.max_combo) < 0:
        return f"FR-045 negative counter :: {context}"
    if engine.cursor < 0 or engine.cursor > len(engine.target):
        return f"cursor {engine.cursor} outside 0..{len(engine.target)} :: {context}"
    return None


def drive(mode_key, keys):
    """Feed keys until the text is finished, checking invariants after each one.

    Stops at completion rather than feeding past it, so this file tests the
    ledger only — input-after-completion is defect D-29 and has its own test.
    """
    engine, _ = make_engine(TARGET, mode_key)
    fed = []
    for key in keys:
        if engine.is_finished():
            break
        engine.feed_key(key)
        fed.append(key)
        problem = check_invariants(engine, mode_key, fed)
        if problem:
            return problem
    return None


@pytest.mark.parametrize("mode_key", MODES)
def test_ledger_holds_over_randomised_sequences(mode_key):
    """400 sequences x 40 keystrokes per mode, from a fixed seed.

    `lock_on_error` is the interesting case: it is the only mode where the cursor
    can revisit a position, which is what D-08 mishandled. The other two advance
    on every keystroke, so they passed even before the fix.
    """
    rng = random.Random(SEED)
    failures = []
    for _ in range(SEQUENCES_PER_MODE):
        keys = [rng.choice(KEYPOOL) for _ in range(KEYS_PER_SEQUENCE)]
        problem = drive(mode_key, keys)
        if problem:
            failures.append(problem)

    assert not failures, (
        f"{len(failures)}/{SEQUENCES_PER_MODE} sequences broke an invariant. First:\n"
        + failures[0]
    )


@pytest.mark.parametrize("mode_key", MODES)
def test_a_perfectly_typed_run_is_exactly_one_hundred_percent(mode_key):
    """The one sequence whose answer is not in doubt, in every mode. Passes on the
    inherited code — a flawless run involves no error and no Backspace, so none of
    the accounting defects can be reached."""
    engine, _ = make_engine(TARGET, mode_key)
    for ch in TARGET:
        engine.feed_key(ch)
    assert engine.metrics()["accuracy"] == 100.0
    assert engine.errors == 0
    assert engine.total_keystrokes == len(TARGET)


def test_only_typing_can_produce_accuracy():
    """No amount of Backspace pressing may move the counters. This is the
    integrity property behind the 85% unlock gate: without it a student reaches
    100% accuracy and 3 stars without typing a single character."""
    engine, _ = make_engine(TARGET, "backspace")
    for _ in range(200):
        engine.feed_key("\b")

    assert engine.total_keystrokes == 0
    assert engine.correct_keystrokes == 0
    assert engine.metrics()["accuracy"] == 0.0
    assert engine.max_combo == 0


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
@given(
    mode_key=st.sampled_from(MODES),
    keys=st.lists(st.sampled_from(KEYPOOL), min_size=1, max_size=60),
)
@settings(max_examples=300, deadline=None)
def test_ledger_holds_under_hypothesis(mode_key, keys):
    """Same invariants, but with shrinking: a failure reports the shortest key
    sequence that breaks the ledger, which is what makes it debuggable."""
    problem = drive(mode_key, keys)
    assert problem is None, problem
