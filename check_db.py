
import sqlite3

conn = sqlite3.connect("movie_data.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")

print("Database tables:")
for row in cursor.fetchall():
    print(row[0])

conn.close()
