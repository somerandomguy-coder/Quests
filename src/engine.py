"""Progression rules for Quests."""


def calculate_xp_gain(xp_gain: int, current_level: int, current_xp: int) -> tuple[int, int]:
    """Return the new level and carried XP after applying an XP reward.

    TODO: Replace the linear `level * 100` curve with configurable balancing.
    TODO: Consider reward modifiers by difficulty, streaks, and anti-grind rules.
    TODO: Keep progression helpers in this module so UI code stays presentation-only.
    """

    current_level = max(1, current_level)
    current_xp = max(0, current_xp)
    xp_gain = max(0, xp_gain)

    xp_to_level_up = current_level * 100
    total_xp = current_xp + xp_gain

    while total_xp >= xp_to_level_up:
        total_xp -= xp_to_level_up
        current_level += 1
        xp_to_level_up = current_level * 100

    return current_level, total_xp
