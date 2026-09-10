import sqlite3
import os

DB_PATH = 'sql_app.db'

def check_schema():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- POSTS ---")
    cursor.execute("PRAGMA table_info(posts)")
    for col in cursor.fetchall():
        print(col)

    print("\n--- AID_REQUESTS ---")
    cursor.execute("PRAGMA table_info(aid_requests)")
    for col in cursor.fetchall():
        print(col)
        
    conn.close()

if __name__ == "__main__":
    check_schema()
