"""managers/streak_manager.py — decision D4: local-calendar-day streaks,
with a clock-moved-backward guard. See blueprint §2.6 flowchart."""

from datetime import date


class StreakManager:
    def __init__(self, db):
        self.db = db

    def touch(self, profile, today: str) -> None:
        """today: 'YYYY-MM-DD' local date string. Call once on the first
        completed lesson of a session."""
        if not profile.last_active_date:
            profile.current_streak = 1
        elif today == profile.last_active_date:
            pass  # already touched today, no change
        else:
            last = date.fromisoformat(profile.last_active_date)
            cur = date.fromisoformat(today)
            delta_days = (cur - last).days

            if delta_days == 1:
                profile.current_streak += 1
            elif delta_days < 0:
                # Clock moved backward — treat as same day, no punishment.
                pass
            else:
                profile.current_streak = 1  # missed a day (or more)

        profile.longest_streak = max(profile.longest_streak, profile.current_streak)
        profile.last_active_date = today
