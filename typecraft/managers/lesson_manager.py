"""
managers/lesson_manager.py

Loads and validates lessons.json (blueprint §2.3), exposes lessons by
tier, and answers the unlock question (decision D2: accuracy >= 85% on
the previous lesson unlocks the next; WPM never gates progress).
"""

import json

from typecraft.core.logging_setup import get_logger
from typecraft.core.paths import resource_path, writable_data_dir
from typecraft.managers.database import Database
from typecraft.models.lesson import Lesson

log = get_logger(__name__)

SCHEMA_VERSION = 1
UNLOCK_ACCURACY_THRESHOLD = 85.0


class LessonManager:
    def __init__(self, db: Database):
        self.db = db
        self._tiers_raw = []
        self._by_id = {}
        self._ordered = []  # flat list, in tier/order sequence
        #: Human-readable warnings produced while loading lessons.json, surfaced in
        #: the UI via AppContext.notices (FR-024).
        self.warnings = []

    @property
    def _live_path(self):
        return writable_data_dir() / "lessons.json"

    def load_file(self) -> None:
        self.warnings = []
        live_path = self._live_path
        default_path = resource_path("data/lessons.json")

        path_to_read = live_path if live_path.exists() else default_path
        try:
            with open(path_to_read, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("schema_version mismatch")
            self._parse(data)
        except (json.JSONDecodeError, ValueError, KeyError, FileNotFoundError) as exc:
            # Malformed teacher-edited file: fall back to the bundled default
            # and record a warning so the UI can surface it (FR-024, TC-023).
            self.warnings.append(
                "Your edited lessons.json is invalid and has been ignored; "
                "the bundled default lessons are being used."
            )
            log.warning("lessons.json rejected at %s: %s", live_path, exc)
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._parse(data)

    def _parse(self, data: dict) -> None:
        self._tiers_raw = data["tiers"]
        self._by_id = {}
        self._ordered = []
        for tier_block in self._tiers_raw:
            tier_num = tier_block["tier"]
            tier_name = tier_block.get("name", f"Tier {tier_num}")
            tier_color = tier_block.get("color", "#4CAF50")
            for raw in sorted(tier_block["lessons"], key=lambda l: l["order"]):
                lesson = Lesson(
                    id=raw["id"], order=raw["order"], title=raw["title"],
                    finger_focus=raw.get("finger_focus", []),
                    default_mode=raw.get("default_mode", "lock_on_error"),
                    target_wpm=raw.get("target_wpm", 10), lines=raw["lines"],
                    tier=tier_num, tier_name=tier_name, tier_color=tier_color,
                )
                self._by_id[lesson.id] = lesson
                self._ordered.append(lesson)

    def tiers(self) -> list:
        return self._tiers_raw

    def get(self, lesson_id: str) -> Lesson:
        return self._by_id[lesson_id]

    def first_lesson(self):
        return self._ordered[0] if self._ordered else None

    def next_lesson_id(self, lesson_id: str):
        idx = next((i for i, l in enumerate(self._ordered) if l.id == lesson_id), None)
        if idx is None or idx + 1 >= len(self._ordered):
            return None
        return self._ordered[idx + 1].id

    def is_unlocked(self, profile, lesson_id: str) -> bool:
        rows = self.db.query(
            "SELECT is_unlocked FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
            (profile.id, lesson_id),
        )
        return bool(rows and rows[0]["is_unlocked"])

    def unlock_next(self, profile, completed_lesson_id: str, accuracy: float) -> None:
        """Call after a completed attempt is recorded (decision D2)."""
        if accuracy < UNLOCK_ACCURACY_THRESHOLD:
            return
        next_id = self.next_lesson_id(completed_lesson_id)
        if next_id is None:
            return
        existing = self.db.query(
            "SELECT 1 FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
            (profile.id, next_id),
        )
        if existing:
            self.db.execute(
                "UPDATE lesson_progress SET is_unlocked=1 WHERE profile_id=? AND lesson_id=?",
                (profile.id, next_id),
            )
        else:
            self.db.execute(
                "INSERT INTO lesson_progress (profile_id, lesson_id, is_unlocked) VALUES (?, ?, 1)",
                (profile.id, next_id),
            )
