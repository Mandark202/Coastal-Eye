from backend.database import SessionLocal
from backend.models import Alert
import sys

db = SessionLocal()
try:
    alerts = db.query(Alert).all()
    print(f"Total alerts in DB: {len(alerts)}")
    for a in alerts:
        print(f" - {a.title} ({a.location})")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
