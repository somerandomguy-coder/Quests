import sqlite3

def get_connection():
    print("Connecting to database...")
    try:
        con = sqlite3.connect("database.db")
    except Exception as e:
        print("Error while connecting to database")
        raise e
        
    print("Successfully connecting to database")  
    return con

def create_database(con):
    print("Creating database...")
    try:
        cur = con.cursor()
        cur.execute("""
    CREATE TABLE Player(
                    ID TEXT            PRIMARY KEY,
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
    CREATE TABLE Task(
                    ID TEXT,
                    name TEXT,
                    difficulty TEXT,
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
                    
    except Exception as e:
        print("Failed to create database")
        raise e
    print("Successfully created database")
    con.commit()
    return 0




con = get_connection()
create_database(con)
cur = con.cursor()
cur.execute("SELECT * FROM Player;")
res = cur.fetchone()
con.close()
