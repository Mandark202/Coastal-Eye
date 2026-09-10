import sqlite3
import os

DB_PATH = 'sql_app.db'

def fix_schema():
    if not os.path.exists(DB_PATH):
        print("Database not found, skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(posts)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'status' not in columns:
        print("Adding 'status' column to posts table...")
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'Open'")
            conn.commit()
            print("Success.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'status' column already exists.")
        
    conn.close()

if __name__ == "__main__":
    fix_schema()
