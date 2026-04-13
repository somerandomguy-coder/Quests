"""SQLite persistence layer for the Quests MVP."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sqlite3
import uuid
from typing import Any

try:
    from . import engine
except ImportError:
    import engine


LATEST_SCHEMA_VERSION = 2
DEFAULT_IMPORTANT_LEVEL = 50


class DatabaseConnection:
    """Repository layer for player and task persistence."""

    def __init__(self, filename: str | Path):
        self.filename = str(Path(filename))

    def bootstrap(self) -> None:
        Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as con:
            self._migrate_to_latest(con)

    def _get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.filename)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    def _migrate_to_latest(self, con: sqlite3.Connection) -> None:
        existing_tables = set(self._list_tables(con))
        current_version = self._get_user_version(con)

        if not existing_tables:
            self._create_schema(con)
            self._set_user_version(con, LATEST_SCHEMA_VERSION)
            return

        if {"player", "task"}.issubset(existing_tables):
            task_columns = set(self._get_table_columns(con, "task"))
            if "important_level" not in task_columns:
                self._migrate_task_table_v1_to_v2(con)
            self._set_user_version(con, LATEST_SCHEMA_VERSION)
            return

        if "Player" in existing_tables:
            con.execute("ALTER TABLE Player RENAME TO player_legacy;")
        if "Task" in existing_tables:
            con.execute("ALTER TABLE Task RENAME TO task_legacy;")

        self._create_schema(con)
        self._copy_legacy_player_data(con)
        self._copy_legacy_task_data(con)
        self._drop_legacy_tables(con)
        self._set_user_version(con, LATEST_SCHEMA_VERSION)

    def _create_schema(self, con: sqlite3.Connection) -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS player(
                player_id TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                character_class TEXT NOT NULL DEFAULT 'Peasant',
                level INTEGER NOT NULL DEFAULT 1 CHECK(level >= 1),
                xp INTEGER NOT NULL DEFAULT 0 CHECK(xp >= 0),
                xp_full INTEGER NOT NULL DEFAULT 100 CHECK(xp_full > 0),
                last_finish_task TEXT NOT NULL DEFAULT '',
                total_quest_completed INTEGER NOT NULL DEFAULT 0 CHECK(total_quest_completed >= 0),
                easy_quests_completed INTEGER NOT NULL DEFAULT 0 CHECK(easy_quests_completed >= 0),
                medium_quests_completed INTEGER NOT NULL DEFAULT 0 CHECK(medium_quests_completed >= 0),
                hard_quests_completed INTEGER NOT NULL DEFAULT 0 CHECK(hard_quests_completed >= 0),
                streak_count INTEGER NOT NULL DEFAULT 0 CHECK(streak_count >= 0),
                join_date TEXT NOT NULL,
                saved_timestamp TEXT NOT NULL
            );
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS task(
                task_id TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                difficulty INTEGER NOT NULL CHECK(difficulty IN (1, 2, 3)),
                important_level INTEGER NOT NULL DEFAULT 50 CHECK(important_level BETWEEN 0 AND 100),
                description TEXT NOT NULL DEFAULT '',
                current_progress REAL NOT NULL DEFAULT 0 CHECK(current_progress >= 0),
                full_progress REAL NOT NULL DEFAULT 1 CHECK(full_progress > 0),
                reward_xp INTEGER NOT NULL CHECK(reward_xp > 0),
                deadline TEXT,
                is_finished INTEGER NOT NULL DEFAULT 0 CHECK(is_finished IN (0, 1)),
                recurrence TEXT NOT NULL DEFAULT 'none',
                tags TEXT NOT NULL DEFAULT '',
                completed_at TEXT,
                created_at TEXT NOT NULL,
                player_id TEXT NOT NULL,
                FOREIGN KEY(player_id) REFERENCES player(player_id) ON DELETE CASCADE
            );
            """
        )

    def _migrate_task_table_v1_to_v2(self, con: sqlite3.Connection) -> None:
        con.execute(
            f"ALTER TABLE task ADD COLUMN important_level INTEGER NOT NULL DEFAULT {DEFAULT_IMPORTANT_LEVEL} CHECK(important_level BETWEEN 0 AND 100);"
        )
        con.execute(
            """
            UPDATE task
            SET important_level = ?
            WHERE important_level IS NULL;
            """,
            (DEFAULT_IMPORTANT_LEVEL,),
        )

    def reset_database(self) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute("DROP TABLE IF EXISTS task;")
            cur.execute("DROP TABLE IF EXISTS player;")
            self._set_user_version(con, 0)

    def fetch_player(self) -> dict[str, Any] | None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT *
                FROM player
                ORDER BY saved_timestamp DESC
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            if row is None:
                return None

            player = dict(row)
            player.update(self._fetch_player_metrics(con, player["player_id"], player["join_date"]))
            return player

    def fetch_unfinished_tasks(self, player_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM task
            WHERE is_finished = 0
        """
        params: tuple[Any, ...] = ()
        if player_id is not None:
            query += " AND player_id = ?"
            params = (player_id,)
        query += " ORDER BY created_at DESC;"

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [self._map_task_row(row) for row in rows]

    def add_player(self, name: str) -> str:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Name cannot be empty.")

        player_id = str(uuid.uuid4())
        today = date.today().isoformat()
        timestamp = datetime.now().isoformat()

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO player(
                    player_id,
                    name,
                    character_class,
                    level,
                    xp,
                    xp_full,
                    last_finish_task,
                    total_quest_completed,
                    easy_quests_completed,
                    medium_quests_completed,
                    hard_quests_completed,
                    streak_count,
                    join_date,
                    saved_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    player_id,
                    cleaned_name,
                    "Peasant",
                    1,
                    0,
                    100,
                    "",
                    0,
                    0,
                    0,
                    0,
                    0,
                    today,
                    timestamp,
                ),
            )

        return player_id

    def add_new_task(
        self,
        player_id: str,
        name: str,
        difficulty: int | None = None,
        important_level: int | None = None,
        description: str | None = None,
        full_progress: float | None = None,
        reward_xp: int | None = None,
        deadline: str | None = None,
        recurrent: int | None = None,
        recurrence: str | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
    ) -> str:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Task name cannot be empty.")

        difficulty = difficulty or 1
        if difficulty not in {1, 2, 3}:
            raise ValueError("Difficulty must be 1, 2, or 3.")

        important_level = DEFAULT_IMPORTANT_LEVEL if important_level is None else int(important_level)
        if not 0 <= important_level <= 100:
            raise ValueError("Important level must be between 0 and 100.")

        progress_total = full_progress if full_progress is not None else 1.0
        if progress_total <= 0:
            raise ValueError("Full progress must be greater than zero.")

        recurrence_value = self._normalize_recurrence(recurrence, recurrent)
        deadline_value = self._normalize_deadline(deadline)
        tags_value = self._serialize_tags(tags)
        timestamp = datetime.now().isoformat()
        task_id = str(uuid.uuid4())

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO task(
                    task_id,
                    name,
                    difficulty,
                    important_level,
                    description,
                    current_progress,
                    full_progress,
                    reward_xp,
                    deadline,
                    is_finished,
                    recurrence,
                    tags,
                    completed_at,
                    created_at,
                    player_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task_id,
                    cleaned_name,
                    difficulty,
                    important_level,
                    description or "",
                    0.0,
                    progress_total,
                    reward_xp if reward_xp is not None else _default_reward_xp(difficulty),
                    deadline_value,
                    0,
                    recurrence_value,
                    tags_value,
                    None,
                    timestamp,
                    player_id,
                ),
            )

        return task_id

    def add_multiple_new_task(self, player_id: str, tasks: list[Any]) -> int:
        inserted = 0
        for task in tasks:
            payload = task.to_task_payload() if hasattr(task, "to_task_payload") else dict(task)
            try:
                self.add_new_task(
                    player_id,
                    str(payload.get("name", "")),
                    difficulty=int(payload.get("difficulty", 1)),
                    important_level=int(payload.get("important_level", DEFAULT_IMPORTANT_LEVEL)),
                    description=str(payload.get("description", "")),
                    reward_xp=int(payload["reward_xp"]) if payload.get("reward_xp") is not None else None,
                    deadline=str(payload["deadline"]) if payload.get("deadline") else None,
                    recurrence=str(payload["recurrence"]) if payload.get("recurrence") else None,
                    tags=payload.get("tags"),
                )
                inserted += 1
            except (TypeError, ValueError):
                continue
        return inserted

    def update_player_stat(self, xp: int, level: int, player_id: str) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE player
                SET xp = ?, level = ?, xp_full = ?, saved_timestamp = ?
                WHERE player_id = ?;
                """,
                (xp, level, _xp_full_for_level(level), datetime.now().isoformat(), player_id),
            )

    def update_complete_task(self, task_id: str) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE task
                SET is_finished = 1,
                    completed_at = ?
                WHERE task_id = ?;
                """,
                (date.today().isoformat(), task_id),
            )

    def complete_task(
        self, task_id: str, player_id: str, new_xp: int, new_level: int
    ) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT difficulty
                FROM task
                WHERE task_id = ? AND player_id = ?;
                """,
                (task_id, player_id),
            )
            task_row = cur.fetchone()
            if task_row is None:
                raise ValueError("Task was not found for the current player.")

            cur.execute(
                """
                SELECT last_finish_task, streak_count
                FROM player
                WHERE player_id = ?;
                """,
                (player_id,),
            )
            player_row = cur.fetchone()
            if player_row is None:
                raise ValueError("Player was not found.")

            today_iso = date.today().isoformat()
            streak_count = _calculate_streak(
                player_row["last_finish_task"], player_row["streak_count"]
            )
            difficulty = int(task_row["difficulty"])

            cur.execute(
                """
                UPDATE task
                SET is_finished = 1,
                    completed_at = ?
                WHERE task_id = ?;
                """,
                (today_iso, task_id),
            )
            cur.execute(
                """
                UPDATE player
                SET xp = ?,
                    level = ?,
                    xp_full = ?,
                    last_finish_task = ?,
                    total_quest_completed = total_quest_completed + 1,
                    easy_quests_completed = easy_quests_completed + ?,
                    medium_quests_completed = medium_quests_completed + ?,
                    hard_quests_completed = hard_quests_completed + ?,
                    streak_count = ?,
                    saved_timestamp = ?
                WHERE player_id = ?;
                """,
                (
                    new_xp,
                    new_level,
                    _xp_full_for_level(new_level),
                    today_iso,
                    1 if difficulty == 1 else 0,
                    1 if difficulty == 2 else 0,
                    1 if difficulty == 3 else 0,
                    streak_count,
                    datetime.now().isoformat(),
                    player_id,
                ),
            )

    def delete_character(self, player_id: str) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                DELETE FROM player
                WHERE player_id = ?;
                """,
                (player_id,),
            )

    def _fetch_player_metrics(
        self, con: sqlite3.Connection, player_id: str, join_date: str
    ) -> dict[str, Any]:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) AS total_completed,
                COALESCE(SUM(CASE WHEN difficulty = 1 THEN 1 ELSE 0 END), 0) AS easy_completed,
                COALESCE(SUM(CASE WHEN difficulty = 2 THEN 1 ELSE 0 END), 0) AS medium_completed,
                COALESCE(SUM(CASE WHEN difficulty = 3 THEN 1 ELSE 0 END), 0) AS hard_completed
            FROM task
            WHERE player_id = ? AND is_finished = 1;
            """,
            (player_id,),
        )
        completion_row = cur.fetchone()

        today_iso = date.today().isoformat()
        cur.execute(
            """
            SELECT COUNT(*) AS completed_today
            FROM task
            WHERE player_id = ? AND completed_at = ?;
            """,
            (player_id, today_iso),
        )
        today_row = cur.fetchone()

        joined_on = date.fromisoformat(join_date)
        active_days = max(1, (date.today() - joined_on).days + 1)
        total_completed = int(completion_row["total_completed"] or 0)

        return {
            "total_quest_completed": total_completed,
            "easy_quests_completed": int(completion_row["easy_completed"] or 0),
            "medium_quests_completed": int(completion_row["medium_completed"] or 0),
            "hard_quests_completed": int(completion_row["hard_completed"] or 0),
            "completed_today": int(today_row["completed_today"] or 0),
            "efficiency_rating": round(total_completed / active_days, 2),
        }

    def _normalize_deadline(self, deadline: str | None) -> str | None:
        if deadline is None or deadline == "":
            return None
        return date.fromisoformat(deadline).isoformat()

    def _normalize_recurrence(
        self, recurrence: str | None, recurrent: int | None
    ) -> str:
        if recurrence:
            normalized = recurrence.strip().lower()
            if normalized not in {"none", "daily", "weekly", "monthly"}:
                raise ValueError("Recurrence must be none, daily, weekly, or monthly.")
            return normalized
        if recurrent in (None, 0):
            return "none"
        mapping = {1: "daily", 2: "weekly", 3: "monthly"}
        return mapping.get(recurrent, "none")

    def _serialize_tags(self, tags: list[str] | tuple[str, ...] | None) -> str:
        if not tags:
            return ""
        unique_tags = dict.fromkeys(tag.strip().lower() for tag in tags if str(tag).strip())
        return ",".join(unique_tags.keys())

    def _map_task_row(self, row: sqlite3.Row) -> dict[str, Any]:
        mapped = dict(row)
        mapped["tags"] = [tag for tag in mapped.get("tags", "").split(",") if tag]
        return engine.enrich_task_priority(mapped)

    def _list_tables(self, con: sqlite3.Connection) -> list[str]:
        cur = con.cursor()
        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
            """
        )
        return [row["name"] for row in cur.fetchall()]

    def _get_table_columns(self, con: sqlite3.Connection, table_name: str) -> list[str]:
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cur.fetchall()]

    def _get_user_version(self, con: sqlite3.Connection) -> int:
        cur = con.cursor()
        cur.execute("PRAGMA user_version;")
        return int(cur.fetchone()[0])

    def _set_user_version(self, con: sqlite3.Connection, version: int) -> None:
        con.execute(f"PRAGMA user_version = {int(version)};")

    def _copy_legacy_player_data(self, con: sqlite3.Connection) -> None:
        if "player_legacy" not in set(self._list_tables(con)):
            return

        cur = con.cursor()
        cur.execute("SELECT * FROM player_legacy;")
        rows = cur.fetchall()
        for row in rows:
            legacy = dict(row)
            con.execute(
                """
                INSERT INTO player(
                    player_id,
                    name,
                    character_class,
                    level,
                    xp,
                    xp_full,
                    last_finish_task,
                    total_quest_completed,
                    easy_quests_completed,
                    medium_quests_completed,
                    hard_quests_completed,
                    streak_count,
                    join_date,
                    saved_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    legacy.get("playerID"),
                    legacy.get("name") or "Adventurer",
                    legacy.get("characterClass") or "Peasant",
                    max(1, int(legacy.get("level") or 1)),
                    max(0, int(legacy.get("XP") or 0)),
                    max(1, int(legacy.get("XPfull") or 100)),
                    legacy.get("lastFinishTask") or "",
                    max(0, int(legacy.get("totalQuestCompleted") or 0)),
                    max(0, int(legacy.get("easyQuestsCompleted") or 0)),
                    max(0, int(legacy.get("mediumQuestsCompleted") or 0)),
                    max(0, int(legacy.get("hardQuestsCompleted") or 0)),
                    max(0, int(legacy.get("streakCount") or 0)),
                    legacy.get("joinDate") or date.today().isoformat(),
                    legacy.get("savedTimestamp") or datetime.now().isoformat(),
                ),
            )

    def _copy_legacy_task_data(self, con: sqlite3.Connection) -> None:
        if "task_legacy" not in set(self._list_tables(con)):
            return

        cur = con.cursor()
        cur.execute("SELECT * FROM task_legacy;")
        rows = cur.fetchall()
        for row in rows:
            legacy = dict(row)
            con.execute(
                """
                INSERT INTO task(
                    task_id,
                    name,
                    difficulty,
                    important_level,
                    description,
                    current_progress,
                    full_progress,
                    reward_xp,
                    deadline,
                    is_finished,
                    recurrence,
                    tags,
                    completed_at,
                    created_at,
                    player_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    legacy.get("TaskID"),
                    legacy.get("name") or "Untitled Quest",
                    min(max(int(legacy.get("difficulty") or 1), 1), 3),
                    DEFAULT_IMPORTANT_LEVEL,
                    legacy.get("description") or "",
                    float(legacy.get("currentProgress") or 0.0),
                    max(float(legacy.get("fullProgress") or 1.0), 1.0),
                    max(int(legacy.get("rewardXP") or 10), 1),
                    legacy.get("deadline"),
                    1 if int(legacy.get("finish") or 0) else 0,
                    self._normalize_recurrence(None, legacy.get("recurrent")),
                    "",
                    date.today().isoformat() if int(legacy.get("finish") or 0) else None,
                    datetime.now().isoformat(),
                    legacy.get("playerID"),
                ),
            )

    def _drop_legacy_tables(self, con: sqlite3.Connection) -> None:
        con.execute("DROP TABLE IF EXISTS player_legacy;")
        con.execute("DROP TABLE IF EXISTS task_legacy;")


def _default_reward_xp(difficulty: int) -> int:
    if difficulty == 3:
        return 100
    if difficulty == 2:
        return 50
    return 10


def _xp_full_for_level(level: int) -> int:
    normalized_level = max(1, level)
    return 100 + ((normalized_level - 1) * 25)


def _calculate_streak(last_finish_task: str | None, current_streak: int | None) -> int:
    today = date.today()
    current_streak = current_streak or 0

    if not last_finish_task:
        return 1

    try:
        previous_date = date.fromisoformat(last_finish_task)
    except ValueError:
        return 1

    if previous_date == today:
        return max(1, current_streak)
    if previous_date == today - timedelta(days=1):
        return max(1, current_streak) + 1
    return 1


Database_Connection = DatabaseConnection
