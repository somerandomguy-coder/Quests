"""Markdown import helpers for Quest definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


QUEST_SEPARATOR = "---"
ALLOWED_DIFFICULTIES = {1, 2, 3}
SUPPORTED_FIELDS = {
    "description",
    "difficulty",
    "reward",
    "reward xp",
    "deadline",
    "recurrence",
    "recurrent",
    "tags",
    "important",
    "importance",
    "important level",
}


@dataclass(frozen=True)
class QuestImportRecord:
    name: str
    description: str = ""
    difficulty: int = 1
    reward_xp: int = 10
    deadline: str | None = None
    recurrence: str | None = None
    tags: tuple[str, ...] = ()
    important_level: int = 50

    def to_task_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "reward_xp": self.reward_xp,
            "deadline": self.deadline,
            "recurrence": self.recurrence,
            "tags": list(self.tags),
            "important_level": self.important_level,
        }


@dataclass(frozen=True)
class QuestImportIssue:
    block_index: int
    message: str
    quest_name: str | None = None


@dataclass
class QuestImportResult:
    quests: list[QuestImportRecord] = field(default_factory=list)
    issues: list[QuestImportIssue] = field(default_factory=list)

    @property
    def imported_count(self) -> int:
        return len(self.quests)

    @property
    def warning_count(self) -> int:
        return len(self.issues)


def parse_markdown_quests(file_path: str | Path) -> QuestImportResult:
    """Parse markdown quest blocks into structured quest import results."""

    content = Path(file_path).read_text(encoding="utf-8")
    result = QuestImportResult()
    seen_names: set[str] = set()

    for block_index, block in enumerate(_split_blocks(content), start=1):
        if not block.strip():
            continue

        record, issues = _parse_quest_block(block, block_index, seen_names)
        result.issues.extend(issues)
        if record is not None:
            result.quests.append(record)
            seen_names.add(_normalize_name(record.name))

    return result


def _split_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.strip() == QUEST_SEPARATOR:
            blocks.append("\n".join(current_lines).strip())
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        blocks.append("\n".join(current_lines).strip())

    return blocks


def _parse_quest_block(
    block: str, block_index: int, seen_names: set[str]
) -> tuple[QuestImportRecord | None, list[QuestImportIssue]]:
    issues: list[QuestImportIssue] = []
    name: str | None = None
    field_values: dict[str, str] = {}

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if name is None and line.startswith("#"):
            title = line.lstrip("#").strip()
            if ":" in title:
                prefix, value = title.split(":", 1)
                if prefix.strip().lower() == "quest":
                    name = value.strip()
                    continue

        parsed_field = _parse_metadata_line(line)
        if parsed_field is None:
            continue

        key, value = parsed_field
        if key not in SUPPORTED_FIELDS:
            issues.append(
                QuestImportIssue(
                    block_index=block_index,
                    quest_name=name,
                    message=f"Ignored unsupported field '{key}'.",
                )
            )
            continue
        field_values[key] = value

    if not name:
        issues.append(
            QuestImportIssue(
                block_index=block_index,
                quest_name=None,
                message="Skipped block without a '# QUEST:' title.",
            )
        )
        return None, issues

    normalized_name = _normalize_name(name)
    if normalized_name in seen_names:
        issues.append(
            QuestImportIssue(
                block_index=block_index,
                quest_name=name,
                message="Skipped duplicate quest name in the same import file.",
            )
        )
        return None, issues

    try:
        difficulty = _parse_difficulty(field_values.get("difficulty"))
        reward_xp = _parse_reward_xp(
            field_values.get("reward xp") or field_values.get("reward"),
            difficulty,
        )
        deadline = _parse_deadline(field_values.get("deadline"))
        recurrence = _parse_recurrence(
            field_values.get("recurrence") or field_values.get("recurrent")
        )
        tags = _parse_tags(field_values.get("tags"))
        important_level = _parse_importance(
            field_values.get("important level")
            or field_values.get("importance")
            or field_values.get("important")
        )
    except ValueError as error:
        issues.append(
            QuestImportIssue(
                block_index=block_index,
                quest_name=name,
                message=str(error),
            )
        )
        return None, issues

    return (
        QuestImportRecord(
            name=name,
            description=field_values.get("description", ""),
            difficulty=difficulty,
            reward_xp=reward_xp,
            deadline=deadline,
            recurrence=recurrence,
            tags=tags,
            important_level=important_level,
        ),
        issues,
    )


def _parse_metadata_line(line: str) -> tuple[str, str] | None:
    if not line.startswith(("-", "*")):
        return None

    body = line[1:].strip()
    if not body or ":" not in body:
        return None

    key_part, value = body.split(":", 1)
    key = key_part.replace("*", "").strip().lower()
    return key, value.strip()


def _parse_difficulty(raw_value: str | None) -> int:
    if raw_value is None or raw_value == "":
        return 1

    difficulty = int(raw_value)
    if difficulty not in ALLOWED_DIFFICULTIES:
        raise ValueError("Difficulty must be 1, 2, or 3.")
    return difficulty


def _parse_reward_xp(raw_value: str | None, difficulty: int) -> int:
    if raw_value is None or raw_value == "":
        return _default_reward_xp(difficulty)

    reward_value = raw_value.strip().split()[0]
    reward_xp = int(reward_value)
    if reward_xp <= 0:
        raise ValueError("Reward XP must be greater than zero.")
    return reward_xp


def _parse_deadline(raw_value: str | None) -> str | None:
    if raw_value is None or raw_value == "":
        return None

    parsed = date.fromisoformat(raw_value.strip())
    return parsed.isoformat()


def _parse_recurrence(raw_value: str | None) -> str | None:
    if raw_value is None or raw_value == "":
        return None

    recurrence = raw_value.strip().lower()
    if recurrence not in {"daily", "weekly", "monthly"}:
        raise ValueError("Recurrence must be daily, weekly, or monthly.")
    return recurrence


def _parse_tags(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None or raw_value == "":
        return ()

    tags = tuple(
        dict.fromkeys(
            tag.strip().lower()
            for tag in raw_value.split(",")
            if tag.strip()
        )
    )
    return tags


def _parse_importance(raw_value: str | None) -> int:
    if raw_value is None or raw_value == "":
        return 50

    important_level = int(raw_value.strip().split()[0])
    if not 0 <= important_level <= 100:
        raise ValueError("Important level must be between 0 and 100.")
    return important_level


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _default_reward_xp(difficulty: int) -> int:
    if difficulty == 3:
        return 100
    if difficulty == 2:
        return 50
    return 10
