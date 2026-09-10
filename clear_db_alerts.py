from backend.database import SessionLocal
from backend.models import Alert

def clear_alerts():
    db = SessionLocal()
    try:
        num = db.query(Alert).delete()
        db.commit()
        print(f"Cleared {num} old alerts from the database.")
    except Exception as e:
        print(f"Error clearing alerts: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_alerts()
