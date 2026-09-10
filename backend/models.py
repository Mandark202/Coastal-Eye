from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .database import Base

def get_ist_time():
    # Helper to get current time in IST (Naive for SQLite storage ease)
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # 'user' or 'authority'

    posts = relationship("Post", back_populates="owner")
    aid_requests = relationship("AidRequest", back_populates="user")

class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, index=True) # Using string ID to match frontend's "p_..." format if needed, or we can use UUID
    location = Column(String)
    caption = Column(String)
    description = Column(Text)
    image_data = Column(Text) # Storing base64 string for simplicity in hackathon
    
    created_at = Column(DateTime, default=get_ist_time)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # "AI" fields
    risk_score = Column(Integer, default=0)
    
    # Community interaction
    likes = Column(Integer, default=0)
    status = Column(String, default="Open") # Open, Resolved, Dismissed
    
    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    created_at = Column(DateTime, default=get_ist_time)
    post_id = Column(String, ForeignKey("posts.id"))
    
    post = relationship("Post", back_populates="comments")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String)
    # Geo-coordinates for distance sorting
    lat = Column(Float)
    lon = Column(Float)
    
    title = Column(String)
    message = Column(String)
    severity = Column(String) # High, Medium, Low
    alert_type = Column(String) # Cyclone, Algal Bloom, etc.
    source = Column(String, default="Unknown") # e.g. Satellite, IoT
    created_at = Column(DateTime, default=get_ist_time)

class AidRequest(Base):
    __tablename__ = "aid_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=get_ist_time)
    
    # New fields for Advanced Hub
    description = Column(String, default="")
    needs = Column(String, default="General") # Food, Medical, Rescue
    urgency = Column(String, default="Medium") # High, Medium, Low
    urgency_score = Column(Integer, default=0) # AI calculated score (0-100)
    status = Column(String, default="Pending") # Pending, In Progress, Resolved
    contact = Column(String, default="")
    location = Column(String, default="Unknown")

    user = relationship("User", back_populates="aid_requests")

class VoiceSOS(Base):
    __tablename__ = "voice_sos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Optional link to user
    transcript = Column(Text)
    category = Column(String)
    severity = Column(Integer) # 0-100 severity score
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=get_ist_time)

class FakeReportAnalysis(Base):
    __tablename__ = "fake_report_analysis"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, index=True) # ID of the post/report being analyzed
    authenticity_score = Column(Integer) # 0-100
    trust_level = Column(String) # Trusted, Suspicious, Critical Review
    duplicate_probability = Column(Integer)
    spam_probability = Column(Integer)
    geo_mismatch = Column(Boolean, default=False)
    flagged_keywords = Column(String) # Comma-separated
    created_at = Column(DateTime, default=get_ist_time)

class ResourceCenter(Base):
    __tablename__ = "resource_centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    available_ambulances = Column(Integer, default=5)
    available_medical_kits = Column(Integer, default=50)
    available_food_packets = Column(Integer, default=200)
    available_rescue_boats = Column(Integer, default=2)
    created_at = Column(DateTime, default=get_ist_time)

class ResourceAllocation(Base):
    __tablename__ = "resource_allocations"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer) # ID of AidRequest
    resource_center_id = Column(Integer, ForeignKey("resource_centers.id"))
    allocated_resource = Column(String) # Ambulance, Medical Kit, etc.
    quantity = Column(Integer)
    priority_score = Column(Integer) # 0-100
    dispatch_status = Column(String, default="Pending") # Pending, Dispatched, Arrived
    estimated_arrival = Column(String) # e.g., "15 mins"
    created_at = Column(DateTime, default=get_ist_time)

class HospitalFacility(Base):
    __tablename__ = "hospital_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    zone = Column(String, default="Coastal")
    contact_number = Column(String, default="112")
    total_beds = Column(Integer, default=100)
    occupied_beds = Column(Integer, default=60)
    icu_beds_total = Column(Integer, default=20)
    icu_beds_occupied = Column(Integer, default=12)
    oxygen_status = Column(String, default="Sufficient") # Sufficient, Moderate, Critical
    trauma_center = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)

    @property
    def available_beds(self):
        return max(0, self.total_beds - self.occupied_beds)

    @property
    def available_icu_beds(self):
        return max(0, self.icu_beds_total - self.icu_beds_occupied)

    @property
    def occupancy_rate(self):
        return round((self.occupied_beds / max(1, self.total_beds)) * 100, 1)

class ShelterFacility(Base):
    __tablename__ = "shelter_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    zone = Column(String, default="Coastal")
    contact_number = Column(String, default="1070")
    total_capacity = Column(Integer, default=500)
    current_occupancy = Column(Integer, default=200)
    food_status = Column(String, default="Full") # Full, Moderate, Depleted
    water_status = Column(String, default="Potable Available") # Potable Available, Limited, Depleted
    generator_power = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)

    @property
    def available_capacity(self):
        return max(0, self.total_capacity - self.current_occupancy)

    @property
    def occupancy_rate(self):
        return round((self.current_occupancy / max(1, self.total_capacity)) * 100, 1)

class EmergencyDispatch(Base):
    __tablename__ = "emergency_dispatches"

    id = Column(Integer, primary_key=True, index=True)
    cad_id = Column(String, unique=True, index=True) # e.g. ERSS-112-GOA-2026-0812
    sos_id = Column(Integer, nullable=True)
    aid_request_id = Column(Integer, nullable=True)
    caller_phone = Column(String, default="Unknown")
    category = Column(String, default="General")
    urgency = Column(String, default="HIGH")
    latitude = Column(Float)
    longitude = Column(Float)
    location_name = Column(String, default="Coastal Zone")
    transcript = Column(Text, default="")
    primary_agency = Column(String, default="ERSS 112 Emergency Operations Center")
    regional_helpline = Column(String, default="112")
    dispatch_status = Column(String, default="Transmitted to 112 ERSS") # Transmitted to 112 ERSS, Acknowledged by EOC, Dispatched
    created_at = Column(DateTime, default=get_ist_time)

class IncidentChatMessage(Base):
    __tablename__ = "incident_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, index=True) # links to cad_id or sos_{id}
    sender_role = Column(String, default="citizen") # "citizen" or "authority"
    sender_name = Column(String, default="Citizen")
    message = Column(Text)
    status = Column(String, default="delivered") # sent, delivered, read
    created_at = Column(DateTime, default=get_ist_time)

class SocialSignal(Base):
    __tablename__ = "social_signals"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, default="Twitter/X") # Twitter/X, Telegram, Koo, Regional Social
    author_handle = Column(String, default="@coastal_citizen")
    author_name = Column(String, default="Coastal Watcher")
    author_avatar = Column(String, default="")
    text = Column(Text)
    language = Column(String, default="en")
    
    # Geolocation & Geofence
    location_name = Column(String, default="Coastal Zone")
    latitude = Column(Float)
    longitude = Column(Float)
    geo_zone = Column(String, default="West Coast")
    
    # Threat & NLP Analysis
    threat_category = Column(String, default="Flood Surge") # Flood Surge, Boat Distress, Cyclone Swell, Toxic Slick, Erosion
    risk_score = Column(Integer, default=50) # 0-100 calculated by AI NLP engine
    matched_keywords = Column(String, default="") # JSON list or comma separated
    urgency_level = Column(String, default="High") # Critical, High, Moderate, Low
    
    # Early Warning & Cross-referencing
    early_warning_status = Column(String, default="PRE_OFFICIAL_LEAD") # PRE_OFFICIAL_LEAD, CONFIRMED_ALERT, ESCALATED_OFFICIAL, RESOLVED
    lead_time_minutes = Column(Integer, default=45) # Minutes caught before official report
    cross_referenced_alert_id = Column(Integer, nullable=True) # ID of matching official alert if one was created
    
    # Social Telemetry
    repost_count = Column(Integer, default=12)
    like_count = Column(Integer, default=48)
    velocity_score = Column(Float, default=8.4) # Posts/min spike velocity
    verified_local = Column(Boolean, default=True) # Local geofence verified
    confidence_score = Column(Float, default=0.92) # 0.0 - 1.0
    
    created_at = Column(DateTime, default=get_ist_time)


# ─── Missing Person / Family Reunification Models ────────────────────────────

class MissingPerson(Base):
    """A report of someone who is missing after a disaster."""
    __tablename__ = "missing_persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, default="Unknown")  # Male, Female, Other, Unknown

    # Last known whereabouts
    last_seen_location = Column(String, default="Unknown")
    last_seen_lat = Column(Float, nullable=True)
    last_seen_lon = Column(Float, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    # Description
    description = Column(Text, default="")
    photo_data = Column(Text, nullable=True)  # base64 image (optional)

    # Reporter details
    reporter_name = Column(String, default="Anonymous")
    reporter_contact = Column(String, default="")

    # Status tracking
    status = Column(String, default="Missing")  # Missing, Safe, Found

    created_at = Column(DateTime, default=get_ist_time)
    updated_at = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)


class SafetyDeclaration(Base):
    """A self-declaration that a person is safe."""
    __tablename__ = "safety_declarations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer, nullable=True)
    current_location = Column(String, default="Unknown")
    contact = Column(String, default="")
    message = Column(Text, default="")  # Optional personal message

    created_at = Column(DateTime, default=get_ist_time)


class ShelterCheckin(Base):
    """A check-in record when someone is registered at a cyclone shelter."""
    __tablename__ = "shelter_checkins"

    id = Column(Integer, primary_key=True, index=True)
    shelter_id = Column(Integer, ForeignKey("shelter_facilities.id"), nullable=True)
    shelter_name = Column(String, default="")  # Denormalized for quick display

    person_name = Column(String, index=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, default="Unknown")
    notes = Column(Text, default="")

    reported_by = Column(String, default="Shelter Staff")  # Staff name
    checkin_time = Column(DateTime, default=get_ist_time)

    shelter = relationship("ShelterFacility", foreign_keys=[shelter_id])
