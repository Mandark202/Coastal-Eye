import sqlite3

def fix_database():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(alerts)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'source' not in columns:
            print("Adding missing column 'source' to alerts table...")
            cursor.execute("ALTER TABLE alerts ADD COLUMN source VARCHAR DEFAULT 'Unknown'")
            conn.commit()
            print("Database fixed successfully.")
        else:
            print("Column 'source' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()
