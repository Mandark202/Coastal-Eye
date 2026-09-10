import sqlite3
import os

DB_PATH = 'sql_app.db'

def add_score_column():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(aid_requests)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'urgency_score' not in columns:
        print("Adding 'urgency_score' column to aid_requests table...")
        try:
            cursor.execute("ALTER TABLE aid_requests ADD COLUMN urgency_score INTEGER DEFAULT 0")
            conn.commit()
            print("Success.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'urgency_score' column already exists.")
        
    conn.close()

if __name__ == "__main__":
    add_score_column()
