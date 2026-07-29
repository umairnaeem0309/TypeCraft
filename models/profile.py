"""models/profile.py — the Profile data holder, mirrors the PROFILES table."""

from dataclasses import dataclass


@dataclass
class Profile:
    id: int
    name: str
    avatar_key: str
    total_xp: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: str = ""
    created_at: str = ""
