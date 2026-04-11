"""Markdown import helpers for Quest definitions."""

from __future__ import annotations

from pathlib import Path
import re


QUEST_SEPARATOR_PATTERN = re.compile(r"^\s*---\s*$", re.MULTILINE)


def parse_markdown_quests(file_path: str | Path) -> list[dict[str, int | str]]:
    """Parse markdown quest blocks into structured task dictionaries.

    The parser intentionally skips malformed blocks instead of raising so the UI
    can continue importing valid quests from partially-correct AI output.

    TODO: Replace regex parsing with a small schema-aware parser.
    TODO: Return import warnings/errors alongside successful quest records.
    TODO: Detect duplicates before persistence.
    TODO: Support more optional fields such as deadline, recurrence, and tags.
    """

    content = Path(file_path).read_text(encoding="utf-8")
    parsed_quests: list[dict[str, int | str]] = []

    for block in QUEST_SEPARATOR_PATTERN.split(content):
        quest_data = _parse_quest_block(block)
        if quest_data is not None:
            parsed_quests.append(quest_data)

    return parsed_quests


def _parse_quest_block(block: str) -> dict[str, int | str] | None:
    name_match = re.search(r"^\s*#\s*QUEST:\s*(.+?)\s*$", block, re.MULTILINE)
    if not name_match:
        return None

    name = name_match.group(1).strip()
    if not name:
        return None

    description_match = re.search(
        r"\*\*Description\*\*:\s*(.+)", block, re.IGNORECASE
    )
    difficulty_match = re.search(
        r"\*\*Difficulty\*\*:\s*(\d+)", block, re.IGNORECASE
    )
    reward_match = re.search(r"\*\*Reward\*\*:\s*(\d+)", block, re.IGNORECASE)

    difficulty = int(difficulty_match.group(1)) if difficulty_match else 1
    if difficulty not in {1, 2, 3}:
        return None

    reward_xp = int(reward_match.group(1)) if reward_match else _default_reward_xp(
        difficulty
    )
    if reward_xp <= 0:
        return None

    return {
        "name": name,
        "description": description_match.group(1).strip() if description_match else "",
        "difficulty": difficulty,
        "reward_xp": reward_xp,
    }


def _default_reward_xp(difficulty: int) -> int:
    if difficulty == 3:
        return 100
    if difficulty == 2:
        return 50
    return 10
