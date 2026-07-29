"""
engine/input_modes.py

The Strategy pattern for wrong-key behaviour (blueprint decision D1).
TypingEngine never contains mode-specific branching — it holds one
InputMode and delegates every keystroke to it.

Locked decision on backspace correction (BackspaceMode only, since it's
the only mode where Backspace is allowed at all):
  - Correcting a previously-flagged ERROR character DOES retroactively
    fix the bookkeeping: `errors` is decremented and `correct_keystrokes`
    is incremented for that position, so final accuracy reflects the
    corrected text, not the original mistake. This is the more
    child-friendly reading of "self-correction" — a student who catches
    and fixes their own mistake should see that reflected in their score.
  - `combo` is NOT restored by a correction. It already broke at the
    moment of the original error and stays broken; correcting a past
    character does not un-break a streak that has since moved on. Only
    fresh consecutive correct keystrokes rebuild combo.
"""

from abc import ABC, abstractmethod

from TypeCraft.models.attempt import CharStatus, KeystrokeResult


class InputMode(ABC):
    """Abstract base. One instance is chosen per lesson on ModeSelect."""

    @abstractmethod
    def resolve(self, state, typed_char: str) -> KeystrokeResult:
        """
        state: the owning TypingEngine (read cursor/target/char_status from it,
               but do not mutate engine counters here — TypingEngine.feed_key()
               applies the returned KeystrokeResult).
        typed_char: the character just typed, or "\\b" to signal Backspace.
        """
        raise NotImplementedError

    @abstractmethod
    def allows_backspace(self) -> bool:
        raise NotImplementedError


class LockOnErrorMode(InputMode):
    """Cursor does not advance on a wrong key; student must retype it correctly.
    Best for youngest beginners — no way to 'run away' from a mistake."""

    def allows_backspace(self) -> bool:
        return False

    def resolve(self, state, typed_char: str) -> KeystrokeResult:
        if typed_char == "\b":
            # Backspace is a no-op in this mode.
            return KeystrokeResult(advanced=False, is_error=False,
                                    char_status=state.char_status[state.cursor]
                                    if state.cursor < len(state.target) else CharStatus.PENDING)

        expected = state.target[state.cursor]
        if typed_char == expected:
            return KeystrokeResult(advanced=True, is_error=False, char_status=CharStatus.CORRECT)
        else:
            # Wrong key: flash red, do NOT advance, error is recorded once
            # per attempt at this position (engine guards against double-count).
            return KeystrokeResult(advanced=False, is_error=True, char_status=CharStatus.ERROR)


class BackspaceMode(InputMode):
    """Advances regardless of correctness; wrong chars are marked red and
    can be fixed with Backspace. For confident learners practising
    self-correction."""

    def allows_backspace(self) -> bool:
        return True

    def resolve(self, state, typed_char: str) -> KeystrokeResult:
        if typed_char == "\b":
            if state.cursor == 0:
                return KeystrokeResult(advanced=False, is_error=False, char_status=CharStatus.PENDING)

            fix_index = state.cursor - 1
            was_error = state.char_status[fix_index] == CharStatus.ERROR
            # Retroactive correction: only meaningful if the char being
            # backed over was flagged wrong. Re-typing it below will fix it.
            return KeystrokeResult(
                advanced=False,
                is_error=False,
                char_status=CharStatus.PENDING,
                is_backspace=True,
                corrected_index=fix_index if was_error else -1,
            )

        expected = state.target[state.cursor]
        if typed_char == expected:
            return KeystrokeResult(advanced=True, is_error=False, char_status=CharStatus.CORRECT)
        else:
            return KeystrokeResult(advanced=True, is_error=True, char_status=CharStatus.ERROR)


class FreeAdvanceMode(InputMode):
    """Always advances; wrong characters stay red and uncorrected.
    Speed drills / exam-style runs. No backspace."""

    def allows_backspace(self) -> bool:
        return False

    def resolve(self, state, typed_char: str) -> KeystrokeResult:
        if typed_char == "\b":
            return KeystrokeResult(advanced=False, is_error=False, char_status=CharStatus.PENDING)

        expected = state.target[state.cursor]
        if typed_char == expected:
            return KeystrokeResult(advanced=True, is_error=False, char_status=CharStatus.CORRECT)
        else:
            return KeystrokeResult(advanced=True, is_error=True, char_status=CharStatus.ERROR)


MODE_REGISTRY = {
    "lock_on_error": LockOnErrorMode,
    "backspace": BackspaceMode,
    "free_advance": FreeAdvanceMode,
}


def create_mode(mode_key: str) -> InputMode:
    cls = MODE_REGISTRY.get(mode_key)
    if cls is None:
        raise ValueError(f"Unknown input mode: {mode_key!r}")
    return cls()
