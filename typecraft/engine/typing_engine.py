"""
engine/typing_engine.py

Drives one lesson attempt. Owns the target text, cursor, per-char status,
and running counters. Delegates every keystroke's rule to the active
InputMode (blueprint §1.5) and stays mode-agnostic itself — it never
branches on which mode is active.

Public contract (frozen per §4.2):
    feed_key(char)   -> KeystrokeResult
    metrics()        -> dict
    is_finished()    -> bool
    result()         -> AttemptResult
"""

import time

from typecraft.engine.input_modes import InputMode
from typecraft.models.attempt import AttemptResult, AttemptStatus, CharStatus, KeystrokeResult
from typecraft.engine import metrics as m


class TypingEngine:
    def __init__(self, target: str, mode: InputMode, profile_id: int, lesson_id: str,
                 mode_key: str, tier: int, clock=time.monotonic):
        # clock is injected so WPM is deterministic under test: a fake clock lets a
        # scripted attempt assert an exact words-per-minute value instead of sleeping.
        # Production always uses time.monotonic (immune to system clock changes).
        self._clock = clock
        self.target = target
        self.mode = mode
        self.profile_id = profile_id
        self.lesson_id = lesson_id
        self.mode_key = mode_key
        self.tier = tier

        self.cursor = 0
        self.char_status = [CharStatus.PENDING] * len(target)

        self.total_keystrokes = 0
        self.errors = 0
        self.correct_keystrokes = 0

        self.combo = 0
        self.max_combo = 0

        # Backspace corrections of a previously-wrong character. Reported to the
        # student, never scored (OQ-001).
        self.corrections_made = 0

        self._start_time = None
        self._end_time = None
        self._started_at_iso = None

    @staticmethod
    def _ignored() -> KeystrokeResult:
        """A keystroke the engine declines to act on. Nothing is counted."""
        return KeystrokeResult(advanced=False, is_error=False, char_status=CharStatus.PENDING)

    def feed_key(self, char: str) -> KeystrokeResult:
        """char is a single typed character, or '\\b' for Backspace."""
        # FR-047: once the target text is complete the attempt is over and every
        # further key is ignored. This must come BEFORE mode.resolve(), which
        # indexes target[cursor] — the old ordering made the equivalent guard
        # below unreachable and raised IndexError instead (defect D-29).
        if self.is_finished():
            return self._ignored()

        if char == "\b" and not self.mode.allows_backspace():
            return self._ignored()

        if self._start_time is None and char != "\b":
            self._start_time = self._clock()
            self._started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

        result = self.mode.resolve(self, char)

        if result.is_backspace:
            self._apply_backspace(result)
            return result

        # From here the keystroke is scored, and posts exactly one ledger entry:
        # total goes up by one, and so does exactly one of correct/errors. That
        # is what makes FR-043 (correct + errors == total) true by construction.
        self.total_keystrokes += 1

        if result.is_error:
            # Every wrong keystroke is its own mistake, including a repeat at the
            # same position in LockOnErrorMode. Suppressing repeats unbalanced the
            # ledger and under-reported the mistake count (defect D-08).
            self.errors += 1
            self.combo = 0
        else:
            self.correct_keystrokes += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

        self.char_status[self.cursor] = result.char_status

        if result.advanced:
            self.cursor += 1

        if self.is_finished():
            self._end_time = self._clock()

        return result

    def _apply_backspace(self, result: KeystrokeResult) -> None:
        """Move the cursor back one position and clear what it uncovers.

        Deliberately counter-neutral (OQ-001): no metric is touched here. The
        previous version decremented `errors` and incremented
        `correct_keystrokes`, then the retype credited the same position a
        second time — crediting a keystroke that was never pressed and reporting
        100% accuracy for any fully-corrected attempt (defect D-07).

        Combo is not restored: it broke when the original error was made.
        """
        if self.cursor == 0:
            return  # nothing to go back to

        self.cursor -= 1
        self.char_status[self.cursor] = CharStatus.PENDING

        if result.corrected_index != -1:
            # The uncovered character was wrong, so this is a genuine
            # self-correction rather than plain navigation. Reported, not scored.
            self.corrections_made += 1

    def _elapsed_minutes(self) -> float:
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else self._clock()
        return max(0.0, (end - self._start_time) / 60.0)

    def metrics(self) -> dict:
        """Live-readable stats, safe to call every frame the HUD needs a refresh."""
        minutes = self._elapsed_minutes()
        acc = m.accuracy_pct(self.correct_keystrokes, self.total_keystrokes)
        return {
            "accuracy": acc,
            "wpm_gross": m.gross_wpm(self.total_keystrokes, minutes),
            "wpm_net": m.net_wpm(self.correct_keystrokes, minutes),
            "combo": self.combo,
            "max_combo": self.max_combo,
            "errors": self.errors,
            "total_keystrokes": self.total_keystrokes,
            "correct_keystrokes": self.correct_keystrokes,
            "corrections_made": self.corrections_made,
            "cursor": self.cursor,
            "total_chars": len(self.target),
            "elapsed_sec": minutes * 60.0,
        }

    def is_finished(self) -> bool:
        return self.cursor >= len(self.target)

    def result(self, status: AttemptStatus = None) -> AttemptResult:
        """Builds the final AttemptResult. Pass status=INCOMPLETE explicitly
        when called from a mid-lesson quit (decision D3); otherwise COMPLETE
        is inferred from is_finished()."""
        minutes = self._elapsed_minutes()
        acc = m.accuracy_pct(self.correct_keystrokes, self.total_keystrokes)
        wpm_n = m.net_wpm(self.correct_keystrokes, minutes)
        wpm_g = m.gross_wpm(self.total_keystrokes, minutes)
        stars = m.stars_for(acc)
        xp = m.xp_for(acc, wpm_n, stars, self.tier)

        if status is None:
            status = AttemptStatus.COMPLETE if self.is_finished() else AttemptStatus.INCOMPLETE

        return AttemptResult(
            profile_id=self.profile_id,
            lesson_id=self.lesson_id,
            status=status,
            mode=self.mode_key,
            wpm_net=wpm_n,
            wpm_gross=wpm_g,
            accuracy=acc,
            total_keystrokes=self.total_keystrokes,
            errors=self.errors,
            correct_keystrokes=self.correct_keystrokes,
            corrections_made=self.corrections_made,
            combo=self.combo,
            max_combo=self.max_combo,
            duration_sec=minutes * 60.0,
            stars=stars if status == AttemptStatus.COMPLETE else 0,
            xp_awarded=xp if status == AttemptStatus.COMPLETE else 0,
            started_at=self._started_at_iso or "",
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%S") if status == AttemptStatus.COMPLETE else "",
            char_statuses=list(self.char_status),
        )
