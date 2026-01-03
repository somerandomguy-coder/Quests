import sqlite3
from datetime import datetime
import uuid
from sys import exception
from typing import Any

class Database_Connection():
    def __init__(self, filename="database.db"):
        self.filename = filename

    def _get_connection(self) -> sqlite3.Connection:
        print("Connecting to database...")
        try:
            con = sqlite3.connect(self.filename)
        except Exception as e:
            print("Error while connecting to database!")
            raise e
        print("Successfully connecting to database!")  
        return con
    

    def reset_database(self) -> None:
        print("Dropping database...")
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
        DROP TABLE IF EXISTS Player;
                        """)
            cur.execute("""
        DROP TABLE IF EXISTS Task;
                        """)
            con.commit()
            print("Successfully drop database!")
        except Exception as e:
            raise e
        con.close()

    def create_database(self) -> None:
        print("Creating database...")
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
        CREATE TABLE IF NOT EXISTS Player(
                        playerID TEXT            PRIMARY KEY,
                        name TEXT,
                        level INTEGER,
                        XP INTEGER,
                        XPfull INTEGER,
                        lastFinishTask TEXT,
                        streakCount INTEGER,
                        savedTimestamp TEXT 
                        );
                        """)
            cur.execute("""
        CREATE TABLE IF NOT EXISTS Task(
                        TaskID TEXT,
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
                        FOREIGN KEY(playerID) REFERENCES Player(playerID)
                        );""")
            con.commit()
            print("Successfully created database!")
        except Exception as e:
            print("Failed to create database!")
            raise e
        con.close()

    def fetch_unfinished_tasks(self) -> list[tuple[Any]]:
        res = []
        print("Fetch unfinished tasks!")
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
            SELECT * FROM Task 
                where finish = 0;
                        """)
            res = cur.fetchall()
            print("Successfully fetch database!")
        except Exception as e:
            print("Failed to fetch database!")
            raise e
        con.close()
        return res

    def seed_initial_data(self):
        try:
            con = self._get_connection()
            cur = con.cursor()
            # 1. Create the Player (The "Main Character")
            # We use INSERT OR IGNORE so we don't create duplicates every time we run
            cur.execute("""
                INSERT OR IGNORE INTO Player (playerID, name, level, XP, XPfull, streakCount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("hero_01", "Adventurer", 1, 50, 100, 0))
            # 2. Create some Tasks
            # difficulty: 1=Easy, 2=Medium, 3=Hard
            sample_tasks = [
                ("task_01", "Drink Water", 1, "Hydration is key", 0.0, 1.0, 10, "2023-12-31", 0, 1, "hero_01"),
                ("task_02", "Clean Fedora System", 2, "Run dnf autoremove", 0.0, 1.0, 50, "2023-12-31", 0, 2, "hero_01"),
                ("task_03", "Finish QuestList MVP", 3, "Get the list working", 0.5, 1.0, 200, "2024-01-07", 0, 0, "hero_01")
            ]
            cur.executemany("""
                INSERT OR IGNORE INTO Task (TaskID, name, difficulty, description, currentProgress, 
                                            fullProgress, rewardXP, deadline, finish, recurrent, playerID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_tasks)
            con.commit()
            print("Seed data planted!")
        except Exception as e:
            print("Failed to seed data!")
            raise e
        con.close() 

    def fetch_player(self):
        print("Fetching player information...")
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
            SELECT * FROM Player 
            ORDER BY savedTimestamp DESC 
            LIMIT 1;
            """)
            res = cur.fetchone()
            print("Successfully fetched player information!")
        except Exception as e:
            print("Failed to seed data!")
            raise e
        con.close()
        return res

    def update_player_stat(self, xp, level, player_id):
        try:
            print("Update player stat...")
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
                           UPDATE Player
                           SET XP = ?, Level = ?
                           WHERE PlayerID = ?;
                           """, (xp, level, player_id))
            con.commit()
            con.close()
            print("Successfully update player stat")
        except Exception as e:
            raise e

    def update_complete_task(self, task_id):
        print("Ticking off task...")    
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
                        UPDATE Task
                        SET finish = 1 
                        WHERE TaskID = ?;
                        """, (task_id,))
            con.commit()
            con.close()
            print("Successfully ticked off task!")
        except Exception as e:
            raise e
    
    def add_new_task(self, player_id, name, difficulty=None, description=None, full_progress=None, reward_xp=None, deadline=None, recurrent=None):
        try:
            if name == "":
                raise Exception("Name can't be empty")
            if difficulty and (difficulty > 3 or difficulty < 1): 
                raise Exception("Please put difficulty in bound")
            if full_progress and full_progress < 0:
                raise Exception("Full progress can not be negative")
            current_date = datetime.now()
            if deadline and deadline < current_date:
                raise Exception("Deadline can not be in the past")
            
            print("Adding new task...")
            task_id = uuid.uuid7() # using timestamp, already sorted 
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
                        INSERT INTO Task(TaskID, name, difficulty, description, currentProgress, 
                                            fullProgress, rewardXP, deadline, finish, recurrent, playerID)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, 0, ?, ?);
                        """, (str(task_id), name, difficulty, description, full_progress, reward_xp, deadline, recurrent, player_id))
            con.commit()
            con.close()
            print("Successfully added new task!")
        except Exception as e:
            raise e

con = Database_Connection()
con.reset_database()
con.create_database()
con.seed_initial_data()
#
print(con.fetch_unfinished_tasks())
print(con.fetch_player())
# con.update_complete_task('task_01')
# con.update_complete_task('task_02')
# con.update_player_xp(90, 'hero_01')
# print(con.fetch_unfinished_tasks())
# print(con.fetch_player())
