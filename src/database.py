import sqlite3
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

    def update_player_xp(self, xp, player_id):
        try:
            print("Update player xp...")
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
                           UPDATE Player
                           SET XP = ?
                           WHERE PlayerID = ?;
                           """, (xp, player_id))
            con.commit()
            con.close()
            print("Successfully update player xp")
        except Exception as e:
            raise e

    def update_player_level(self, level, player_id):
        try:
            print("Update player level...")
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("""
                           UPDATE Player
                           SET Level = ?
                           WHERE PlayerID = ?;
                           """, (level, player_id))
            con.commit()
            con.close()
            print("Successfully update player level")
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
