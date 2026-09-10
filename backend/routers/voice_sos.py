from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import VoiceSOS, IncidentChatMessage
from typing import Optional
import random
from ..ai_logic import analyze_multilingual_voice_sos
from ..services.emergency_dispatch import create_emergency_dispatch

router = APIRouter(prefix="/api", tags=["VoiceSOS"])

class VoiceSOSRequest(BaseModel):
    transcript: str
    lat: float
    lng: float
    user_id: Optional[int] = None
    caller_phone: Optional[str] = "Unknown"

@router.post("/voice-sos")
def submit_voice_sos(req: VoiceSOSRequest, db: Session = Depends(get_db)):
    # 1. Multilingual language detection and severity classification
    analysis = analyze_multilingual_voice_sos(req.transcript)
    category = analysis["category"]
    severity = analysis["severity"]
    detected_lang = analysis["language"]
    lang_name = analysis["language_name"]

    # 2. Persist Voice SOS record
    new_sos = VoiceSOS(
        user_id=req.user_id,
        transcript=req.transcript,
        category=category,
        severity=severity,
        latitude=req.lat,
        longitude=req.lng
    )
    
    db.add(new_sos)
    db.commit()
    db.refresh(new_sos)
    
    # 3. Direct Handoff to 112 ERSS & Regional Coastal Disaster Cell
    urgency_label = "CRITICAL" if severity >= 75 else ("HIGH" if severity >= 50 else "MODERATE")
    dispatch_payload = create_emergency_dispatch(
        db=db,
        sos_id=new_sos.id,
        caller_phone=req.caller_phone or "Unknown",
        category=category,
        urgency=urgency_label,
        lat=req.lat,
        lon=req.lng,
        location_name=f"Coastal Lat {req.lat:.4f}, Lon {req.lng:.4f}",
        transcript=req.transcript
    )

    # 4. Initialize Two-Way Incident Communication Session
    initial_sys_msg = IncidentChatMessage(
        incident_id=dispatch_payload["cad_id"],
        sender_role="authority",
        sender_name="112 Coastal Emergency Command",
        message=f"SOS Received. CAD Incident #{dispatch_payload['cad_id']} activated. Assigned to {dispatch_payload['primary_agency']}. You are in direct two-way contact with command.",
        status="delivered"
    )
    db.add(initial_sys_msg)
    db.commit()

    return {
        "status": "success",
        "message": "SOS logged and dispatched to 112 ERSS",
        "category": category,
        "severity": severity,
        "language": detected_lang,
        "language_name": lang_name,
        "matched_keyword": analysis.get("matched_keyword"),
        "sos_id": new_sos.id,
        "cad_id": dispatch_payload["cad_id"],
        "emergency_dispatch": dispatch_payload
    }
