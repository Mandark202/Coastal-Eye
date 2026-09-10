import sqlite3
from datetime import datetime

def seed_resources():
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    centers = [
        ("Mumbai Coastal HQ", 19.0760, 72.8777, 8, 45, 120, 3),
        ("Mangalore Rescue Hub", 12.9141, 74.8560, 4, 30, 80, 2),
        ("Chennai Emergency Depot", 13.0827, 80.2707, 6, 40, 150, 4),
        ("Kolkata Sentinel base", 22.5726, 88.3639, 5, 25, 100, 2),
        ("Goa Maritime Center", 15.2993, 73.9844, 3, 20, 60, 5)
    ]
    
    for c in centers:
        cursor.execute("""
            INSERT INTO resource_centers 
            (name, latitude, longitude, available_ambulances, available_medical_kits, available_food_packets, available_rescue_boats, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (c[0], c[1], c[2], c[3], c[4], c[5], c[6], datetime.now().isoformat()))
        
    conn.commit()
    conn.close()
    print("Resource Centers seeded successfully!")

if __name__ == "__main__":
    seed_resources()
