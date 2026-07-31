"""
engine/input_modes.py

The Strategy pattern for wrong-key behaviour (blueprint decision D1).
TypingEngine never contains mode-specific branching — it holds one
InputMode and delegates every keystroke to it.

Backspace correction policy (BackspaceMode only, since it is the only mode
where Backspace is allowed at all). Resolved as OQ-001, docs/requirements.md 13 —
this supersedes an earlier note here that claimed the opposite:

  - Backspace is **navigation, not scoring**. It moves the cursor and clears
    the character it uncovers. It never adjusts `total_keystrokes`, `errors`,
    or `correct_keystrokes`, so every character-producing keystroke posts
    exactly one ledger entry that is never reversed. `correct + errors ==
    total` therefore holds by construction, and no keystroke can be invented.
  - A corrected mistake still costs accuracy: wrong key, Backspace, right key
    is two keystrokes and one error, i.e. 50%, not 100%. The previous
    retroactive-credit scheme reported 100% with zero mistakes for any attempt
    whose errors were all corrected (defect D-07), which made a careful
    student and a lucky one indistinguishable.
  - The student still gets credit for noticing, via the non-scoring
    `corrections_made` tally surfaced on the results screen.
  - `combo` is NOT restored by a correction. It broke at the moment of the
    original error and stays broken; only fresh consecutive correct keystrokes
    rebuild it.
"""

from abc import ABC, abstractmethod

from typecraft.models.attempt import CharStatus, KeystrokeResult


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


#: A Backspace that has nothing to go back to. `is_backspace` is True even though
#: nothing happens, and that matters: it is the flag TypingEngine.feed_key() uses
#: to route a keystroke away from the scoring path. Returning False here was
#: defect D-30 — feed_key() fell through and scored the Backspace as a *correct*
#: keystroke, so 20 presses before typing anything gave 100% accuracy, 3 stars,
#: and an unlock with nothing typed. Any "backspace did nothing" result must
#: still say is_backspace=True.
def _inert_backspace() -> KeystrokeResult:
    return KeystrokeResult(advanced=False, is_error=False,
                           char_status=CharStatus.PENDING,
                           is_backspace=True, corrected_index=-1)


class LockOnErrorMode(InputMode):
    """Cursor does not advance on a wrong key; student must retype it correctly.
    Best for youngest beginners — no way to 'run away' from a mistake."""

    def allows_backspace(self) -> bool:
        return False

    def resolve(self, state, typed_char: str) -> KeystrokeResult:
        if typed_char == "\b":
            # Unreachable in practice: feed_key() rejects Backspace before calling
            # resolve() in modes that disallow it. Kept correct anyway so the
            # D-30 hazard cannot reappear if that guard is ever moved.
            return _inert_backspace()

        expected = state.target[state.cursor]
        if typed_char == expected:
            return KeystrokeResult(advanced=True, is_error=False, char_status=CharStatus.CORRECT)
        else:
            # Wrong key: flash red, do NOT advance. Every wrong keystroke counts
            # as its own error — the engine no longer suppresses repeats at one
            # position (that was defect D-08, which broke correct+errors==total).
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
                # Nothing to go back to. Still flagged as a backspace so the
                # engine cannot score it (defect D-30).
                return _inert_backspace()

            fix_index = state.cursor - 1
            was_error = state.char_status[fix_index] == CharStatus.ERROR
            # corrected_index reports whether the student is fixing a mistake
            # (as opposed to merely navigating back over something already
            # correct). The engine uses it only for the non-scoring
            # `corrections_made` tally — it never adjusts a metric.
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
            # Unreachable (see LockOnErrorMode.resolve); correct regardless.
            return _inert_backspace()

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
