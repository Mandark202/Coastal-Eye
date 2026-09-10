import random
import urllib.parse
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import EmergencyDispatch

# Regional Coastal Disaster Cells across India
COASTAL_ZONES = [
    {
        "state": "Goa",
        "code": "GA",
        "lat_min": 14.8, "lat_max": 15.8,
        "lon_min": 73.6, "lon_max": 74.4,
        "agency": "Goa State Disaster Emergency Center (SDMA)",
        "helpline": "1070",
        "local_police": "0832-2419550",
        "sar_agency": "Indian Coast Guard District HQ 11 (Goa)",
        "sar_helpline": "1554"
    },
    {
        "state": "Maharashtra",
        "code": "MH",
        "lat_min": 15.8, "lat_max": 20.2,
        "lon_min": 72.5, "lon_max": 73.6,
        "agency": "Mumbai Disaster Management Control Room & MMB",
        "helpline": "1916",
        "local_police": "112",
        "sar_agency": "Coast Guard Regional HQ (West - Mumbai)",
        "sar_helpline": "1554"
    },
    {
        "state": "Tamil Nadu",
        "code": "TN",
        "lat_min": 8.0, "lat_max": 13.5,
        "lon_min": 79.5, "lon_max": 80.5,
        "agency": "Tamil Nadu State Disaster EOC & Chennai Corp",
        "helpline": "1070",
        "local_police": "112",
        "sar_agency": "Coast Guard Regional HQ (East - Chennai)",
        "sar_helpline": "1554"
    },
    {
        "state": "Kerala",
        "code": "KL",
        "lat_min": 8.1, "lat_max": 12.8,
        "lon_min": 74.8, "lon_max": 77.5,
        "agency": "Kerala State Emergency Operations Centre (KSEOC)",
        "helpline": "1079",
        "local_police": "112",
        "sar_agency": "Coast Guard District HQ 4 (Kochi)",
        "sar_helpline": "1554"
    },
    {
        "state": "Odisha",
        "code": "OD",
        "lat_min": 19.0, "lat_max": 22.0,
        "lon_min": 84.5, "lon_max": 87.5,
        "agency": "Odisha State Disaster Management Authority (OSDMA)",
        "helpline": "1070",
        "local_police": "112",
        "sar_agency": "Coast Guard Station Paradip",
        "sar_helpline": "1554"
    },
    {
        "state": "Gujarat",
        "code": "GJ",
        "lat_min": 20.0, "lat_max": 24.5,
        "lon_min": 68.0, "lon_max": 73.0,
        "agency": "Gujarat State Disaster Management Authority (GSDMA)",
        "helpline": "1077",
        "local_police": "112",
        "sar_agency": "Coast Guard Regional HQ (North-West - Gandhinagar)",
        "sar_helpline": "1554"
    },
    {
        "state": "Andaman & Nicobar",
        "code": "AN",
        "lat_min": 6.5, "lat_max": 14.0,
        "lon_min": 92.0, "lon_max": 94.0,
        "agency": "State Control Room, Directorate of Disaster Management (Port Blair)",
        "helpline": "1077",
        "local_police": "03192-238881",
        "sar_agency": "Coast Guard Regional HQ (A&N - Port Blair)",
        "sar_helpline": "1554"
    }
]

DEFAULT_ZONE = {
    "state": "National ERSS",
    "code": "IND",
    "agency": "National Emergency Response Support System (ERSS 112)",
    "helpline": "112",
    "local_police": "112",
    "sar_agency": "Indian Coast Guard Maritime Rescue Coordination Centre (MRCC)",
    "sar_helpline": "1554"
}

def resolve_coastal_zone(lat: float, lon: float) -> dict:
    """Finds matching coastal response cell from geographic coordinates."""
    if lat is None or lon is None:
        return DEFAULT_ZONE
    
    for zone in COASTAL_ZONES:
        if (zone["lat_min"] <= lat <= zone["lat_max"] and 
            zone["lon_min"] <= lon <= zone["lon_max"]):
            return zone
            
    return DEFAULT_ZONE

def generate_cad_id(state_code: str) -> str:
    """Generates an official CAD Incident ID matching ERSS standards."""
    now = datetime.now()
    year = now.strftime("%Y")
    rand_num = f"{random.randint(1000, 9999)}"
    return f"ERSS-112-{state_code}-{year}-{rand_num}"

def create_emergency_dispatch(
    db: Session,
    sos_id: int = None,
    aid_request_id: int = None,
    caller_phone: str = "Unknown",
    category: str = "General",
    urgency: str = "HIGH",
    lat: float = 0.0,
    lon: float = 0.0,
    location_name: str = "Coastal Location",
    transcript: str = ""
) -> dict:
    """
    Creates an official ERSS-112 Computer-Aided Dispatch (CAD) packet,
    persists it in DB, and generates direct handoff links & distress beacon triggers.
    """
    zone = resolve_coastal_zone(lat, lon)
    cad_id = generate_cad_id(zone["code"])
    
    dispatch_record = EmergencyDispatch(
        cad_id=cad_id,
        sos_id=sos_id,
        aid_request_id=aid_request_id,
        caller_phone=caller_phone,
        category=category,
        urgency=urgency,
        latitude=lat,
        longitude=lon,
        location_name=location_name,
        transcript=transcript,
        primary_agency=f"{zone['agency']} | {zone['sar_agency']}",
        regional_helpline=zone["helpline"],
        dispatch_status="Transmitted to 112 ERSS & EOC"
    )
    
    db.add(dispatch_record)
    db.commit()
    db.refresh(dispatch_record)
    
    # Generate Pre-filled Distress Beacon URLs
    google_maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else ""
    distress_text = (
        f"🚨 EMERGENCY SOS [Ref: {cad_id}]\n"
        f"Category: {category} ({urgency})\n"
        f"Details: {transcript}\n"
        f"GPS Location: {lat:.5f}, {lon:.5f}\n"
        f"Map: {google_maps_url}\n"
        f"Dispatched via CTAS Coastal Alert System to ERSS 112."
    )
    
    whatsapp_beacon_url = f"https://wa.me/?text={urllib.parse.quote(distress_text)}"
    sms_beacon_url = f"sms:112?body={urllib.parse.quote(distress_text)}"
    
    return {
        "dispatch_id": dispatch_record.id,
        "cad_id": cad_id,
        "category": category,
        "urgency": urgency,
        "status": dispatch_record.dispatch_status,
        "timestamp": dispatch_record.created_at.isoformat() if dispatch_record.created_at else datetime.utcnow().isoformat(),
        "state": zone["state"],
        "primary_agency": zone["agency"],
        "regional_helpline": zone["helpline"],
        "sar_agency": zone["sar_agency"],
        "sar_helpline": zone["sar_helpline"],
        "dial_112_url": "tel:112",
        "dial_sar_url": f"tel:{zone['sar_helpline']}",
        "dial_local_url": f"tel:{zone['helpline']}",
        "whatsapp_beacon_url": whatsapp_beacon_url,
        "sms_beacon_url": sms_beacon_url,
        "gps": {
            "latitude": lat,
            "longitude": lon,
            "maps_url": google_maps_url
        },
        "transcript": transcript
    }
