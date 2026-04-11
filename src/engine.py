"""Progression rules for Quests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressionConfig:
    base_xp_per_level: int = 100
    per_level_growth: int = 25
    difficulty_bonus_by_tier: tuple[float, float, float] = (1.0, 1.2, 1.45)
    streak_bonus_per_day: float = 0.04
    anti_grind_easy_threshold: int = 5
    anti_grind_easy_penalty: float = 0.08
    min_reward_multiplier: float = 0.65
    max_reward_multiplier: float = 1.9


DEFAULT_PROGRESSION = ProgressionConfig()


def xp_required_for_level(
    level: int, config: ProgressionConfig = DEFAULT_PROGRESSION
) -> int:
    normalized_level = max(1, level)
    return config.base_xp_per_level + ((normalized_level - 1) * config.per_level_growth)


def calculate_reward_xp(
    base_reward_xp: int,
    *,
    difficulty: int = 1,
    streak_count: int = 0,
    completed_today: int = 0,
    config: ProgressionConfig = DEFAULT_PROGRESSION,
) -> int:
    """Balance quest rewards using difficulty, streak, and anti-grind modifiers."""

    reward_xp = max(1, int(base_reward_xp))
    difficulty_index = min(max(1, difficulty), 3) - 1
    multiplier = config.difficulty_bonus_by_tier[difficulty_index]

    streak_bonus = min(max(0, streak_count), 14) * config.streak_bonus_per_day
    multiplier += streak_bonus

    if difficulty == 1 and completed_today > config.anti_grind_easy_threshold:
        overflow = completed_today - config.anti_grind_easy_threshold
        multiplier -= overflow * config.anti_grind_easy_penalty

    multiplier = max(config.min_reward_multiplier, multiplier)
    multiplier = min(config.max_reward_multiplier, multiplier)
    return max(1, round(reward_xp * multiplier))


def calculate_xp_gain(
    xp_gain: int,
    current_level: int,
    current_xp: int,
    *,
    config: ProgressionConfig = DEFAULT_PROGRESSION,
) -> tuple[int, int]:
    """Return the new level and carried XP after applying an XP reward."""

    current_level = max(1, current_level)
    current_xp = max(0, current_xp)
    xp_gain = max(0, xp_gain)

    xp_to_level_up = xp_required_for_level(current_level, config)
    total_xp = current_xp + xp_gain

    while total_xp >= xp_to_level_up:
        total_xp -= xp_to_level_up
        current_level += 1
        xp_to_level_up = xp_required_for_level(current_level, config)

    return current_level, total_xp
