import sqlite3

class DB:
    def __init__(self):
        self.conn = sqlite3.connect("sample.db")
        self.c = self.conn.cursor()
        self.c.execute("""
          CREATE TABLE IF NOT EXISTS videos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date TEXT NOT NULL, 
          hour INTEGER NOT NULL,
          minute INTEGER NOT NULL,
          second INTEGER NOT NULL,
          slong INTEGER NOT NULL
        )
        """
        )  
        self.conn.commit()

    def __del__(self):
        self.conn.close()
    
    def insert(self, date, hour, minute, second, slong):
        self.c.execute("INSERT INTO videos (date, hour, minute, second, slong) VALUES (?, ?, ?, ?, ?)", (date, hour, minute, second, slong))
        self.conn.commit()
    
    def select(self):
        self.c.execute("SELECT * FROM videos")
        rows = self.c.fetchall()
        print("id", "date", "hour", "minute", "second", "slong")
        for row in rows:
            print(row)
        return self.c.fetchall()
    
    def delete(self):
        self.c.execute("DELETE FROM videos")
        self.conn.commit()
        self.c.execute("VACUUM")
        self.conn.commit()

if __name__ == "__main__":
    db = DB()
    db.select()