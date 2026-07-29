"""models/lesson.py — parsed representation of one lesson from lessons.json."""

from dataclasses import dataclass, field


@dataclass
class Lesson:
    id: str
    order: int
    title: str
    finger_focus: list
    default_mode: str
    target_wpm: int
    lines: list
    tier: int
    tier_name: str = ""
    tier_color: str = "#4CAF50"

    def target_text(self) -> str:
        """
        Join this lesson's drill lines into one continuous typing target.

        Locked decision: lines are joined with a single space. The student
        never presses Enter mid-lesson — the cursor flows straight through
        from one line into the next, and the WPM clock (T in blueprint §2.4)
        runs continuously from the first keystroke to the last, uninterrupted
        by line boundaries. This keeps the engine's target a single flat
        string and keeps KeyboardRenderer free of any need to highlight
        an Enter key.
        """
        return " ".join(self.lines)
