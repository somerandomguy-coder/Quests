"""Progression and task-priority rules for Quests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


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


@dataclass(frozen=True)
class TaskPriorityConfig:
    mission_quota_by_difficulty: dict[int, int]
    urgency_horizon_days: int = 21
    no_deadline_urgency: int = 0
    max_urgency: int = 100


DEFAULT_PROGRESSION = ProgressionConfig()
DEFAULT_TASK_PRIORITY = TaskPriorityConfig(mission_quota_by_difficulty={3: 1, 2: 3, 1: 5})


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


def enrich_task_priority(
    task: dict[str, Any],
    *,
    today: date | None = None,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> dict[str, Any]:
    today = today or date.today()
    enriched = dict(task)

    days_until_deadline = calculate_days_until_deadline(task.get("deadline"), today=today)
    urgency_score = calculate_urgency_score(
        days_until_deadline,
        config=config,
    )
    important_level = max(0, min(100, int(task.get("important_level") or 0)))
    difficulty = max(1, min(3, int(task.get("difficulty") or 1)))

    enriched["days_until_deadline"] = days_until_deadline
    enriched["urgency_score"] = urgency_score
    enriched["priority_score"] = calculate_priority_score(
        important_level,
        urgency_score,
        difficulty,
    )
    return enriched


def calculate_days_until_deadline(
    deadline: str | None,
    *,
    today: date | None = None,
) -> int | None:
    if not deadline:
        return None

    today = today or date.today()
    deadline_date = date.fromisoformat(deadline)
    return (deadline_date - today).days


def calculate_urgency_score(
    days_until_deadline: int | None,
    *,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> int:
    if days_until_deadline is None:
        return config.no_deadline_urgency
    if days_until_deadline <= 0:
        return config.max_urgency
    if days_until_deadline >= config.urgency_horizon_days:
        return 1

    scaled = config.max_urgency - int(
        (days_until_deadline / config.urgency_horizon_days) * (config.max_urgency - 10)
    )
    return max(1, min(config.max_urgency, scaled))


def calculate_priority_score(
    important_level: int,
    urgency_score: int,
    difficulty: int,
) -> int:
    return (important_level * 1000) + (urgency_score * 10) + difficulty


def rank_tasks_for_priority(
    tasks: list[dict[str, Any]],
    *,
    today: date | None = None,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> list[dict[str, Any]]:
    enriched_tasks = [
        enrich_task_priority(task, today=today, config=config)
        for task in tasks
    ]
    return sorted(
        enriched_tasks,
        key=lambda task: (
            task["important_level"],
            task["urgency_score"],
            task["difficulty"],
            task.get("created_at", ""),
        ),
        reverse=True,
    )


def split_tasks_for_current_mission(
    tasks: list[dict[str, Any]],
    *,
    today: date | None = None,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ranked_tasks = rank_tasks_for_priority(tasks, today=today, config=config)
    mission: list[dict[str, Any]] = []
    backlog: list[dict[str, Any]] = []
    counts_by_difficulty = {1: 0, 2: 0, 3: 0}

    for task in ranked_tasks:
        difficulty = int(task.get("difficulty") or 1)
        quota = config.mission_quota_by_difficulty.get(difficulty, 0)
        if counts_by_difficulty[difficulty] < quota:
            mission.append(task)
            counts_by_difficulty[difficulty] += 1
        else:
            backlog.append(task)

    return mission, backlog


def select_top_priority_tasks(
    tasks: list[dict[str, Any]],
    count: int,
    *,
    today: date | None = None,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> list[dict[str, Any]]:
    return rank_tasks_for_priority(tasks, today=today, config=config)[: max(0, count)]


def group_tasks_by_importance_band(
    tasks: list[dict[str, Any]],
    *,
    today: date | None = None,
    config: TaskPriorityConfig = DEFAULT_TASK_PRIORITY,
) -> dict[str, list[dict[str, Any]]]:
    grouped = {"A": [], "B": [], "C": [], "D": [], "E": []}
    for task in rank_tasks_for_priority(tasks, today=today, config=config):
        important_level = int(task.get("important_level") or 0)
        if important_level >= 85:
            grouped["A"].append(task)
        elif important_level >= 70:
            grouped["B"].append(task)
        elif important_level >= 50:
            grouped["C"].append(task)
        elif important_level >= 30:
            grouped["D"].append(task)
        else:
            grouped["E"].append(task)
    return grouped
