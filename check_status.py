
import sqlite3

conn = sqlite3.connect("movie_data.db")
cursor = conn.cursor()

cursor.execute("""
SELECT omdb_response_status, COUNT(*)
FROM movies
GROUP BY omdb_response_status
ORDER BY omdb_response_status
""")

print("OMDb Enrichment Status:")

for row in cursor.fetchall():
    print(row[0], ":", row[1])

conn.close()
