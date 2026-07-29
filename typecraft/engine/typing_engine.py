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
                 mode_key: str, tier: int):
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

        self._start_time = None
        self._end_time = None
        self._started_at_iso = None

        # Tracks which target-indices have already counted an error, so a
        # student re-attempting the same position in LockOnErrorMode isn't
        # double-penalised for every retry of a single mistake.
        self._error_counted = [False] * len(target)

    def feed_key(self, char: str) -> KeystrokeResult:
        """char is a single typed character, or '\\b' for Backspace."""
        if self._start_time is None and char != "\b":
            self._start_time = time.monotonic()
            self._started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

        if char == "\b" and not self.mode.allows_backspace():
            return KeystrokeResult(advanced=False, is_error=False, char_status=CharStatus.PENDING)

        result = self.mode.resolve(self, char)

        if result.is_backspace:
            self._apply_backspace(result)
            return result

        if self.cursor >= len(self.target):
            return result  # already finished, ignore stray input

        self.total_keystrokes += 1

        if result.is_error:
            if not self._error_counted[self.cursor]:
                self.errors += 1
                self._error_counted[self.cursor] = True
            self.combo = 0
        else:
            self.correct_keystrokes += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

        self.char_status[self.cursor] = result.char_status

        if result.advanced:
            self.cursor += 1

        if self.is_finished():
            self._end_time = time.monotonic()

        return result

    def _apply_backspace(self, result: KeystrokeResult) -> None:
        if self.cursor > 0:
            self.cursor -= 1
            self.char_status[self.cursor] = CharStatus.PENDING

        # Retroactive correction (BackspaceMode locked decision, see
        # engine/input_modes.py docstring): fixing a previously-flagged
        # error decrements errors and increments correct_keystrokes so
        # final accuracy reflects the corrected text. Combo is NOT restored.
        if result.corrected_index != -1 and self._error_counted[result.corrected_index]:
            self.errors -= 1
            self.correct_keystrokes += 1
            self._error_counted[result.corrected_index] = False

    def _elapsed_minutes(self) -> float:
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.monotonic()
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
            combo=self.combo,
            max_combo=self.max_combo,
            duration_sec=minutes * 60.0,
            stars=stars if status == AttemptStatus.COMPLETE else 0,
            xp_awarded=xp if status == AttemptStatus.COMPLETE else 0,
            started_at=self._started_at_iso or "",
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%S") if status == AttemptStatus.COMPLETE else "",
            char_statuses=list(self.char_status),
        )
