from backend.database import SessionLocal, engine, Base
from backend.models import User, Post, AidRequest, Alert
from datetime import datetime

# Recreate tables (reset DB)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Seed Users
    auth_user = User(
        name="Coastal Admin",
        email="authority@coastaleye.com",
        # In a real app, use hashed passwords
        hashed_password="passwordnotreallyhashed",
        role="authority"
    )
    db.add(auth_user)
    
    reg_user = User(
        name="John Doe",
        email="user@example.com",
        hashed_password="passwordnotreallyhashed",
        role="user"
    )
    db.add(reg_user)
    db.commit()
    
    user_id = reg_user.id
    
    # 1. Seed Posts with different priorities
    posts = [
        Post(
            id="p_disaster",
            location="Miami South Beach",
            caption="Tsunami Warning / Flooding",
            description="Massive waves hitting the shore. SOS! Drowning reported.",
            image_data="",
            risk_score=95, # AI should score this very high
            user_id=user_id
        ),
        Post(
            id="p_storm",
            location="Galveston Pier",
            caption="Severe Storm Coming",
            description="Wind speeds picking up significantly. Possible storm surge.",
            image_data="",
            risk_score=65, # Medium-high
            user_id=user_id
        ),
        Post(
            id="p_algae",
            location="Goa North",
            caption="Algal Bloom Spotted",
            description="Green patches in the water near the beach.",
            image_data="",
            risk_score=25, # Low
            user_id=user_id
        )
    ]
    for p in posts:
        db.add(p)

    # 2. Seed Aid Requests with different urgencies
    aid_reqs = [
        AidRequest(
            user_id=user_id,
            description="Elderly person trapped in flooded basement. Need immediate rescue!",
            needs="Rescue",
            urgency="High",
            contact="911-555-0101",
            location="Miami Beach, FL"
        ),
        AidRequest(
            user_id=user_id,
            description="Running out of clean drinking water after the storm.",
            needs="Food/Water",
            urgency="Medium",
            contact="555-0102",
            location="Miami Coastal East"
        ),
        AidRequest(
            user_id=user_id,
            description="Beach trash cleanup requested after high tide.",
            needs="General",
            urgency="Low",
            contact="555-0103",
            location="North Shore"
        )
    ]
    for req in aid_reqs:
        db.add(req)

    db.commit()
    print("Database reset and seeded with prioritized data!")

finally:
    db.close()
