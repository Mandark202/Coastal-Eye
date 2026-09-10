import sqlite3

def add_column():
    conn = sqlite3.connect('coastaleye.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'Open'")
        print("Successfully added 'status' column to posts table.")
    except sqlite3.OperationalError as e:
        print(f"Error (column might already exist): {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_column()
