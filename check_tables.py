import sqlite3

try:
    conn = sqlite3.connect("movie_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")

    tables = cursor.fetchall()

    print("\nDATABASE TABLES")
    print("----------------")

    for table in tables:
        print(table[0])

    conn.close()

except Exception as e:
    print("Error:", e)