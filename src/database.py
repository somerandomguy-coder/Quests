import sqlite3
from sys import exception
from typing import Any

class Database_Connection():
    def __init__(self, filename="database.db"):
        self.con = self.get_connection(filename) 
        self.filename = filename

    def get_connection(self, filename) -> sqlite3.Connection:
        print("Connecting to database...")
        try:
            con = sqlite3.connect(filename)
        except Exception as e:
            print("Error while connecting to database!")
            raise e
        print("Successfully connecting to database!")  
        return con
    

    def reset_database(self) -> None:
        print("Dropping database...")
        try:
            cur = self.con.cursor()
            cur.execute("""
        DROP TABLE IF EXISTS Player;
                        """)
            cur.execute("""
        DROP TABLE IF EXISTS Task;
                        """)
            self.con.commit()
            print("Successfully drop database!")
        except sqlite3.ProgrammingError:
            self.con = self.get_connection(self.filename)
            self.reset_database() 
        except Exception as e:
            raise e

    def create_database(self) -> None:
        print("Creating database...")
        try:
            cur = self.con.cursor()
            cur.execute("""
        CREATE TABLE IF NOT EXISTS Player(
                        playerID TEXT            PRIMARY KEY,
                        name TEXT,
                        level TEXT,
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
            self.con.commit()
            print("Successfully created database!")
        except sqlite3.ProgrammingError:
            self.con = self.get_connection(self.filename)
            self.create_database() 
        except Exception as e:
            print("Failed to create database!")
            raise e
        finally:
            self.con.close()

    def fetch_unfinished_tasks(self) -> list[tuple[Any]]:
        res = []
        print("Fetch unfinished tasks!")
        try:
            cur = self.con.cursor()
            cur.execute("""
            SELECT * FROM Task 
                where finish = 0;
                        """)
            res = cur.fetchall()
            print("Successfully fetch database!")
        except sqlite3.ProgrammingError:
            self.con = self.get_connection(self.filename)
            self.fetch_unfinished_tasks() 
        except Exception as e:
            print("Failed to fetch database!")
            raise e
        finally:
            self.con.close()
        return res

    def seed_initial_data(self):
        try:
            cur = self.con.cursor()
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
            self.con.commit()
            print("Seed data planted!")
        except sqlite3.ProgrammingError:
            self.con = self.get_connection(self.filename)
            self.seed_initial_data() 
        except Exception as e:
            print("Failed to seed data!")
            raise e
    
    def fetch_player(self):
        print("Fetching player information...")
        try:
            cur = self.con.cursor()
            cur.execute("""
            SELECT * FROM Player 
            ORDER BY savedTimestamp DESC 
            LIMIT 1;
            """)
            res = cur.fetchone()
            print("Successfully fetched player information!")
        except sqlite3.ProgrammingError:
            self.con = self.get_connection(self.filename)
            self.fetch_player() 
        except Exception as e:
            print("Failed to seed data!")
            raise e
        finally:
            self.con.close()
        return res

