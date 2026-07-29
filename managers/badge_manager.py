"""managers/badge_manager.py — evaluates and awards the 10 badges (§2.5).
Badge catalogue text lives in data/badges.json; this file only holds the
*criteria* (predicates), since "when is a badge earned" is logic, not
teacher-editable content."""

import time

from TypeCraft.core.paths import resource_path, writable_data_dir
import json


class BadgeManager:
    def __init__(self, db, lesson_manager):
        self.db = db
        self.lesson_manager = lesson_manager
        self._catalogue = {}  # code -> {id, name, description, xp_bonus}
        self._load_catalogue()

    def _load_catalogue(self) -> None:
        live = writable_data_dir() / "badges.json"
        path = live if live.exists() else resource_path("data/badges.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data["badges"]:
            existing = self.db.query("SELECT id FROM badges WHERE code=?", (entry["code"],))
            if existing:
                badge_id = existing[0]["id"]
            else:
                badge_id = self.db.execute(
                    "INSERT INTO badges (code, name, description, xp_bonus) VALUES (?,?,?,?)",
                    (entry["code"], entry["name"], entry["description"], entry["xp_bonus"]),
                )
            self._catalogue[entry["code"]] = {**entry, "id": badge_id}

    def evaluate(self, profile, attempt) -> list:
        """Runs after a completed attempt + streak/level updates. Returns
        list of newly-awarded badge codes."""
        earned_codes = {r["code"] for r in self.db.query(
            """SELECT b.code FROM profile_badges pb
               JOIN badges b ON b.id = pb.badge_id WHERE pb.profile_id=?""",
            (profile.id,),
        )}

        newly_awarded = []
        for code, predicate in self._predicates(profile, attempt).items():
            if code in earned_codes:
                continue
            if predicate():
                self.award(profile, code)
                newly_awarded.append(code)
        return newly_awarded

    def award(self, profile, code: str) -> None:
        badge = self._catalogue[code]
        self.db.execute(
            "INSERT INTO profile_badges (profile_id, badge_id, earned_at) VALUES (?,?,?)",
            (profile.id, badge["id"], time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
        profile.total_xp += badge["xp_bonus"]

    def _predicates(self, profile, attempt) -> dict:
        def completed_count():
            rows = self.db.query(
                "SELECT COUNT(*) as c FROM lesson_attempts WHERE profile_id=? AND status='complete'",
                (profile.id,),
            )
            return rows[0]["c"]

        def tier1_all_complete():
            tier1_ids = [l.id for l in self.lesson_manager._ordered if l.tier == 1]
            if not tier1_ids:
                return False
            rows = self.db.query(
                """SELECT DISTINCT lesson_id FROM lesson_attempts
                   WHERE profile_id=? AND status='complete'""",
                (profile.id,),
            )
            done = {r["lesson_id"] for r in rows}
            return all(lid in done for lid in tier1_ids)

        def triple_star_count():
            rows = self.db.query(
                "SELECT COUNT(*) as c FROM lesson_progress WHERE profile_id=? AND best_stars=3",
                (profile.id,),
            )
            return rows[0]["c"]

        from TypeCraft.engine import metrics as m

        return {
            "first_steps": lambda: completed_count() >= 1,
            "home_row_hero": tier1_all_complete,
            "sharp_shooter": lambda: attempt.accuracy >= 100.0,
            "speed_demon": lambda: attempt.wpm_net >= 30,
            "combo_king": lambda: attempt.max_combo >= 50,
            "perfect_week": lambda: profile.current_streak >= 7,
            "triple_star": lambda: triple_star_count() >= 5,
            "rising_star": lambda: profile.level >= 5,
            "keyboard_master": lambda: profile.level >= 10,
            "marathon": lambda: completed_count() >= 25,
        }
