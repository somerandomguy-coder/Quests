"""SQLite persistence layer for the Quests MVP."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sqlite3
import uuid
from typing import Any


class DatabaseConnection:
    """Small repository layer for player and task persistence.

    TODO: Introduce schema versioning/migrations before changing table layouts.
    TODO: Normalize mixed column naming once migrations exist.
    TODO: Tighten constraints for required fields and allowed value ranges.
    TODO: Revisit which derived stats should be stored vs computed on demand.
    """

    def __init__(self, filename: str | Path):
        self.filename = str(Path(filename))

    def bootstrap(self) -> None:
        self.create_database()

    def _get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.filename)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    def reset_database(self) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute("DROP TABLE IF EXISTS Task;")
            cur.execute("DROP TABLE IF EXISTS Player;")

    def create_database(self) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Player(
                    playerID TEXT PRIMARY KEY,
                    name TEXT,
                    characterClass TEXT,
                    level INTEGER,
                    XP INTEGER,
                    XPfull INTEGER,
                    lastFinishTask TEXT,
                    totalQuestCompleted INTEGER,
                    easyQuestsCompleted INTEGER,
                    mediumQuestsCompleted INTEGER,
                    hardQuestsCompleted INTEGER,
                    streakCount INTEGER,
                    joinDate TEXT,
                    savedTimestamp TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Task(
                    TaskID TEXT PRIMARY KEY,
                    name TEXT,
                    difficulty INTEGER,
                    description TEXT,
                    currentProgress REAL,
                    fullProgress REAL,
                    rewardXP INTEGER,
                    deadline TEXT,
                    finish INTEGER,
                    recurrent INTEGER,
                    playerID TEXT,
                    FOREIGN KEY(playerID) REFERENCES Player(playerID) ON DELETE CASCADE
                );
                """
            )

    def fetch_player(self) -> dict[str, Any] | None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT *
                FROM Player
                ORDER BY savedTimestamp DESC
                LIMIT 1;
                """
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def fetch_unfinished_tasks(self, player_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM Task
            WHERE finish = 0
        """
        params: tuple[Any, ...] = ()
        if player_id is not None:
            query += " AND playerID = ?"
            params = (player_id,)
        query += " ORDER BY difficulty DESC, rowid DESC;"

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def add_player(self, name: str) -> str:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Name cannot be empty.")

        player_id = str(uuid.uuid4())
        today = date.today().isoformat()

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO Player(
                    playerID,
                    name,
                    characterClass,
                    level,
                    XP,
                    XPfull,
                    lastFinishTask,
                    totalQuestCompleted,
                    easyQuestsCompleted,
                    mediumQuestsCompleted,
                    hardQuestsCompleted,
                    streakCount,
                    joinDate,
                    savedTimestamp
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
                    today,
                ),
            )

        return player_id

    def add_new_task(
        self,
        player_id: str,
        name: str,
        difficulty: int | None = None,
        description: str | None = None,
        full_progress: float | None = None,
        reward_xp: int | None = None,
        deadline: str | None = None,
        recurrent: int | None = None,
    ) -> str:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Task name cannot be empty.")

        difficulty = difficulty or 1
        if difficulty not in {1, 2, 3}:
            raise ValueError("Difficulty must be 1, 2, or 3.")

        if full_progress is not None and full_progress < 0:
            raise ValueError("Full progress cannot be negative.")

        task_id = str(uuid.uuid4())

        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO Task(
                    TaskID,
                    name,
                    difficulty,
                    description,
                    currentProgress,
                    fullProgress,
                    rewardXP,
                    deadline,
                    finish,
                    recurrent,
                    playerID
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task_id,
                    cleaned_name,
                    difficulty,
                    description or "",
                    0.0,
                    full_progress if full_progress is not None else 1.0,
                    reward_xp if reward_xp is not None else _default_reward_xp(difficulty),
                    deadline,
                    0,
                    recurrent or 0,
                    player_id,
                ),
            )

        return task_id

    def add_multiple_new_task(
        self, player_id: str, tasks: list[dict[str, Any]]
    ) -> int:
        task_tuples: list[tuple[Any, ...]] = []

        for task in tasks:
            name = str(task.get("name", "")).strip()
            if not name:
                continue

            difficulty = int(task.get("difficulty", 1))
            if difficulty not in {1, 2, 3}:
                continue

            reward_xp = task.get("reward_xp")
            reward_xp = (
                int(reward_xp)
                if reward_xp is not None
                else _default_reward_xp(difficulty)
            )
            if reward_xp <= 0:
                continue

            task_tuples.append(
                (
                    str(uuid.uuid4()),
                    name,
                    difficulty,
                    str(task.get("description", "") or ""),
                    0.0,
                    1.0,
                    reward_xp,
                    None,
                    0,
                    0,
                    player_id,
                )
            )

        if not task_tuples:
            return 0

        with self._get_connection() as con:
            cur = con.cursor()
            cur.executemany(
                """
                INSERT INTO Task(
                    TaskID,
                    name,
                    difficulty,
                    description,
                    currentProgress,
                    fullProgress,
                    rewardXP,
                    deadline,
                    finish,
                    recurrent,
                    playerID
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                task_tuples,
            )

        return len(task_tuples)

    def update_player_stat(self, xp: int, level: int, player_id: str) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE Player
                SET XP = ?, level = ?, XPfull = ?, savedTimestamp = ?
                WHERE playerID = ?;
                """,
                (xp, level, max(1, level) * 100, datetime.now().isoformat(), player_id),
            )

    def update_complete_task(self, task_id: str) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE Task
                SET finish = 1
                WHERE TaskID = ?;
                """,
                (task_id,),
            )

    def complete_task(
        self, task_id: str, player_id: str, new_xp: int, new_level: int
    ) -> None:
        with self._get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT difficulty
                FROM Task
                WHERE TaskID = ? AND playerID = ?;
                """,
                (task_id, player_id),
            )
            task_row = cur.fetchone()
            if task_row is None:
                raise ValueError("Task was not found for the current player.")

            cur.execute(
                """
                SELECT lastFinishTask, streakCount
                FROM Player
                WHERE playerID = ?;
                """,
                (player_id,),
            )
            player_row = cur.fetchone()
            if player_row is None:
                raise ValueError("Player was not found.")

            streak_count = _calculate_streak(
                player_row["lastFinishTask"], player_row["streakCount"]
            )
            difficulty = int(task_row["difficulty"] or 1)

            cur.execute(
                """
                UPDATE Task
                SET finish = 1
                WHERE TaskID = ?;
                """,
                (task_id,),
            )
            cur.execute(
                """
                UPDATE Player
                SET XP = ?,
                    level = ?,
                    XPfull = ?,
                    lastFinishTask = ?,
                    totalQuestCompleted = COALESCE(totalQuestCompleted, 0) + 1,
                    easyQuestsCompleted = COALESCE(easyQuestsCompleted, 0) + ?,
                    mediumQuestsCompleted = COALESCE(mediumQuestsCompleted, 0) + ?,
                    hardQuestsCompleted = COALESCE(hardQuestsCompleted, 0) + ?,
                    streakCount = ?,
                    savedTimestamp = ?
                WHERE playerID = ?;
                """,
                (
                    new_xp,
                    new_level,
                    max(1, new_level) * 100,
                    date.today().isoformat(),
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
                DELETE FROM Player
                WHERE playerID = ?;
                """,
                (player_id,),
            )


def _default_reward_xp(difficulty: int) -> int:
    if difficulty == 3:
        return 100
    if difficulty == 2:
        return 50
    return 10


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
