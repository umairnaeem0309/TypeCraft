"""managers/profile_manager.py — CRUD for student profiles."""

import time

from TypeCraft.managers.database import Database
from TypeCraft.models.profile import Profile


class ProfileManager:
    def __init__(self, db: Database, lesson_manager=None):
        self.db = db
        self.lesson_manager = lesson_manager  # set post-construction by AppContext to avoid a cycle

    def create(self, name: str, avatar_key: str) -> Profile:
        created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        new_id = self.db.execute(
            "INSERT INTO profiles (name, avatar_key, created_at) VALUES (?, ?, ?)",
            (name, avatar_key, created_at),
        )
        profile = Profile(id=new_id, name=name, avatar_key=avatar_key, created_at=created_at)

        # Seed lesson_progress: only the very first lesson (tier 1, order 1)
        # starts unlocked for a brand-new profile. Everything else is locked
        # until the previous lesson clears the D2 accuracy >= 85% bar.
        if self.lesson_manager is not None:
            first = self.lesson_manager.first_lesson()
            if first is not None:
                self.db.execute(
                    "INSERT INTO lesson_progress (profile_id, lesson_id, is_unlocked) VALUES (?, ?, 1)",
                    (new_id, first.id),
                )
        return profile

    def list_all(self) -> list:
        rows = self.db.query("SELECT * FROM profiles ORDER BY created_at ASC")
        return [Profile(**row) for row in rows]

    def load(self, profile_id: int) -> Profile:
        rows = self.db.query("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        if not rows:
            raise ValueError(f"No profile with id {profile_id}")
        return Profile(**rows[0])

    def save(self, profile: Profile) -> None:
        self.db.execute(
            """UPDATE profiles SET name=?, avatar_key=?, total_xp=?, level=?,
               current_streak=?, longest_streak=?, last_active_date=? WHERE id=?""",
            (profile.name, profile.avatar_key, profile.total_xp, profile.level,
             profile.current_streak, profile.longest_streak, profile.last_active_date,
             profile.id),
        )
