import sqlite3
import os

DB_PATH = 'sql_app.db'

def fix_schema():
    if not os.path.exists(DB_PATH):
        print("Database not found, skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check posts table
    cursor.execute("PRAGMA table_info(posts)")
    columns_posts = [info[1] for info in cursor.fetchall()]
    if 'status' not in columns_posts:
        print("Adding 'status' column to posts table...")
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'Open'")
            print("Success.")
        except Exception as e:
            print(f"Error adding column to posts: {e}")
            
    # 2. Check aid_requests table
    cursor.execute("PRAGMA table_info(aid_requests)")
    columns_aid = [info[1] for info in cursor.fetchall()]
    
    required_aid_cols = {
        'description': "TEXT DEFAULT ''",
        'needs': "TEXT DEFAULT 'General'",
        'urgency': "TEXT DEFAULT 'Medium'",
        'status': "TEXT DEFAULT 'Pending'",
        'contact': "TEXT DEFAULT ''",
        'location': "TEXT DEFAULT 'Unknown'"
    }
    
    for col, defn in required_aid_cols.items():
        if col not in columns_aid:
            print(f"Adding '{col}' column to aid_requests table...")
            try:
                cursor.execute(f"ALTER TABLE aid_requests ADD COLUMN {col} {defn}")
                print("Success.")
            except Exception as e:
                print(f"Error adding column {col} to aid_requests: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_schema()
