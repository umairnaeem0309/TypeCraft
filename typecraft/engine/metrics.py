"""
engine/metrics.py

Pure functions only — no state, no I/O. All formulas from blueprint §2.4.
Kept separate from TypingEngine so they're independently unit-testable
with scripted inputs and no window open at all (§1.3).
"""


def accuracy_pct(correct_keystrokes: int, total_keystrokes: int) -> float:
    if total_keystrokes == 0:
        return 0.0
    return (correct_keystrokes / total_keystrokes) * 100.0


def gross_wpm(total_keystrokes: int, minutes: float) -> float:
    if minutes <= 0:
        return 0.0
    return max(0.0, (total_keystrokes / 5.0) / minutes)


def net_wpm(correct_keystrokes: int, minutes: float) -> float:
    if minutes <= 0:
        return 0.0
    return max(0.0, (correct_keystrokes / 5.0) / minutes)


def stars_for(accuracy: float) -> int:
    if accuracy < 85:
        return 0
    if accuracy < 92:
        return 1
    if accuracy < 97:
        return 2
    return 3


def xp_for(accuracy: float, net_wpm_value: float, stars: int, tier: int) -> int:
    """Blueprint §2.4 XP formula. `tier` is 1-indexed (Tier 1..5)."""
    if accuracy < 85:
        return round(5 * accuracy / 100)  # participation only, max 4, no unlock

    speed_bonus = min(net_wpm_value, 40) * 0.5
    star_mult = {1: 1.0, 2: 1.3, 3: 1.6}.get(stars, 1.0)
    tier_mult = 1.0 + 0.1 * (tier - 1)
    return round((20 + speed_bonus) * (accuracy / 100) * star_mult * tier_mult)


def level_for(total_xp: int) -> int:
    """xp_to_reach(L) = 25*(L-1)*L, L capped at 10."""
    level = 1
    for candidate in range(1, 11):
        if xp_to_reach(candidate) <= total_xp:
            level = candidate
        else:
            break
    return level


def xp_to_reach(level: int) -> int:
    return 25 * (level - 1) * level


def daily_streak_bonus(current_streak: int) -> int:
    return 5 * min(current_streak, 5)
