"""The three wrong-key strategies (FR-030..FR-036, blueprint decision D1).

`InputMode.resolve()` is a pure decision function: it reads the engine's cursor,
target and character statuses and returns a KeystrokeResult. It must never mutate
the engine's counters — only TypingEngine.feed_key() does that. These tests drive
the modes through a minimal fake state so a mode's decision can be checked in
isolation from the bookkeeping that consumes it.
"""

import pytest

from typecraft.engine.input_modes import (
    MODE_REGISTRY,
    BackspaceMode,
    FreeAdvanceMode,
    LockOnErrorMode,
    create_mode,
)
from typecraft.models.attempt import CharStatus


class FakeState:
    """The three attributes InputMode.resolve() is allowed to read."""

    def __init__(self, target="abc", cursor=0, statuses=None):
        self.target = target
        self.cursor = cursor
        self.char_status = statuses or [CharStatus.PENDING] * len(target)


# --------------------------------------------------------------------------- registry

def test_registry_holds_exactly_the_three_documented_modes():
    """FR-030."""
    assert set(MODE_REGISTRY) == {"lock_on_error", "backspace", "free_advance"}


@pytest.mark.parametrize("key,cls", [
    ("lock_on_error", LockOnErrorMode),
    ("backspace", BackspaceMode),
    ("free_advance", FreeAdvanceMode),
])
def test_create_mode_builds_the_right_strategy(key, cls):
    assert isinstance(create_mode(key), cls)


def test_unknown_mode_key_raises_rather_than_falling_back():
    """FR-036: a typo'd mode must be a loud programmer error, not a silent
    substitution that quietly changes how a lesson scores."""
    with pytest.raises(ValueError, match="Unknown input mode"):
        create_mode("does_not_exist")


# --------------------------------------------------------------------------- backspace permission

def test_only_backspace_mode_allows_backspace():
    """FR-032/FR-034: Backspace is inert in the other two modes."""
    assert BackspaceMode().allows_backspace() is True
    assert LockOnErrorMode().allows_backspace() is False
    assert FreeAdvanceMode().allows_backspace() is False


# --------------------------------------------------------------------------- LockOnErrorMode

def test_lock_on_error_advances_on_the_expected_key():
    result = LockOnErrorMode().resolve(FakeState("abc", 0), "a")
    assert result.advanced is True
    assert result.is_error is False
    assert result.char_status is CharStatus.CORRECT


def test_lock_on_error_does_not_advance_on_a_wrong_key():
    """FR-032: the cursor stays put so the student cannot run away from a mistake."""
    result = LockOnErrorMode().resolve(FakeState("abc", 0), "z")
    assert result.advanced is False
    assert result.is_error is True
    assert result.char_status is CharStatus.ERROR


def test_lock_on_error_checks_the_character_under_the_cursor_not_the_first_one():
    result = LockOnErrorMode().resolve(FakeState("abc", 2), "c")
    assert result.advanced is True and result.is_error is False


# --------------------------------------------------------------------------- FreeAdvanceMode

@pytest.mark.parametrize("typed,is_error,status", [
    ("a", False, CharStatus.CORRECT),
    ("z", True, CharStatus.ERROR),
])
def test_free_advance_always_advances(typed, is_error, status):
    """FR-034: every printable keystroke moves on; errors stay uncorrected."""
    result = FreeAdvanceMode().resolve(FakeState("abc", 0), typed)
    assert result.advanced is True
    assert result.is_error is is_error
    assert result.char_status is status


def test_free_advance_ignores_backspace():
    result = FreeAdvanceMode().resolve(FakeState("abc", 2), "\b")
    assert result.advanced is False
    assert result.is_error is False
    assert result.is_backspace is False


# --------------------------------------------------------------------------- BackspaceMode

@pytest.mark.parametrize("typed,is_error,status", [
    ("a", False, CharStatus.CORRECT),
    ("z", True, CharStatus.ERROR),
])
def test_backspace_mode_advances_on_correct_and_incorrect(typed, is_error, status):
    """FR-033: both advance; the wrong one is marked red and can be revisited."""
    result = BackspaceMode().resolve(FakeState("abc", 0), typed)
    assert result.advanced is True
    assert result.is_error is is_error
    assert result.char_status is status


def test_backspace_at_the_start_of_the_text_is_a_no_op():
    """Nothing to go back to; must not produce a negative cursor."""
    result = BackspaceMode().resolve(FakeState("abc", 0), "\b")
    assert result.advanced is False
    assert result.is_backspace is False
    assert result.corrected_index == -1


def test_backspace_over_an_error_reports_the_position_being_revisited():
    state = FakeState("abc", 1, [CharStatus.ERROR, CharStatus.PENDING, CharStatus.PENDING])
    result = BackspaceMode().resolve(state, "\b")
    assert result.is_backspace is True
    assert result.corrected_index == 0
    assert result.char_status is CharStatus.PENDING
    assert result.advanced is False


def test_backspace_over_a_correct_character_reports_no_correction():
    """Going back over something already right is navigation, not a correction."""
    state = FakeState("abc", 1, [CharStatus.CORRECT, CharStatus.PENDING, CharStatus.PENDING])
    result = BackspaceMode().resolve(state, "\b")
    assert result.is_backspace is True
    assert result.corrected_index == -1


def test_resolve_does_not_mutate_the_state_it_is_given():
    """The strategy decides; only TypingEngine.feed_key() applies. If a mode ever
    starts mutating, counters and on-screen status can disagree."""
    state = FakeState("abc", 1, [CharStatus.ERROR, CharStatus.PENDING, CharStatus.PENDING])
    before_cursor, before_statuses = state.cursor, list(state.char_status)

    for mode in (LockOnErrorMode(), BackspaceMode(), FreeAdvanceMode()):
        mode.resolve(state, "b")
        mode.resolve(state, "z")
        if mode.allows_backspace():
            mode.resolve(state, "\b")

    assert state.cursor == before_cursor
    assert state.char_status == before_statuses
