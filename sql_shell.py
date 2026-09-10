import sqlite3
import os
import sys

DB_PATH = 'sql_app.db'

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Connected to {DB_PATH}")
    print("Type your SQL commands. Type 'exit', 'quit' or 'q' to leave.")
    print("Type 'tables' to list tables.")
    print("Example: SELECT * FROM users;")

    while True:
        try:
            query = input("sqlite> ").strip()
        except EOFError:
            break
            
        if query.lower() in ('exit', 'quit', 'q'):
            break
        
        if not query:
            continue
            
        if query.lower() == 'tables':
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            
        try:
            cursor.execute(query)
            if query.lower().startswith("select") or query.lower().startswith("pragma"):
                rows = cursor.fetchall()
                # Get column names
                if cursor.description:
                    names = [description[0] for description in cursor.description]
                    print(" | ".join(names))
                    print("-" * (len(" | ".join(names))))
                
                for row in rows:
                    print(row)
            else:
                conn.commit()
                print(f"Rows affected: {cursor.rowcount}")
        except sqlite3.Error as e:
            print(f"Error: {e}")
            
    conn.close()
    print("Bye.")

if __name__ == "__main__":
    main()
