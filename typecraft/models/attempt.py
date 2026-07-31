"""models/attempt.py — data shapes shared by engine, scenes, and the database."""

from dataclasses import dataclass, field
from enum import Enum


class CharStatus(Enum):
    PENDING = "pending"
    CORRECT = "correct"
    ERROR = "error"


class AttemptStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass
class KeystrokeResult:
    """Returned by InputMode.resolve() and consumed by TypingEngine.feed_key()."""
    advanced: bool
    is_error: bool
    char_status: CharStatus
    is_backspace: bool = False
    corrected_index: int = -1  # index of char fixed by a backspace correction, else -1


@dataclass
class AttemptResult:
    """Mirrors the LESSON_ATTEMPTS table column-for-column."""
    profile_id: int
    lesson_id: str
    status: AttemptStatus
    mode: str

    wpm_net: float = 0.0
    wpm_gross: float = 0.0
    accuracy: float = 0.0

    total_keystrokes: int = 0
    errors: int = 0
    correct_keystrokes: int = 0

    #: Backspace corrections the student made (BackspaceMode only). Reported for
    #: encouragement — "you caught 4 of your own mistakes" — and never scored;
    #: see the OQ-001 resolution in docs/requirements.md 13.
    corrections_made: int = 0

    combo: int = 0
    max_combo: int = 0

    duration_sec: float = 0.0
    stars: int = 0
    xp_awarded: int = 0

    started_at: str = ""
    completed_at: str = ""

    char_statuses: list = field(default_factory=list)
