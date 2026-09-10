from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from ..models import IncidentChatMessage, EmergencyDispatch, AidRequest, VoiceSOS

router = APIRouter(prefix="/api/incident-chat", tags=["Incident Two-Way Chat"])

class IncidentChatSendRequest(BaseModel):
    incident_id: str # CAD ID (e.g. ERSS-112-GA-2026-1234) or session ID
    sender_role: str # "citizen" or "authority"
    sender_name: Optional[str] = None
    message: str

@router.post("/send")
def send_incident_message(req: IncidentChatSendRequest, db: Session = Depends(get_db)):
    """Send a two-way message between Citizen and Disaster Command Cell."""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    default_name = "Disaster Command (112 EOC)" if req.sender_role == "authority" else "Citizen"
    sender_name = req.sender_name or default_name

    msg = IncidentChatMessage(
        incident_id=req.incident_id.strip(),
        sender_role=req.sender_role.strip().lower(),
        sender_name=sender_name.strip(),
        message=req.message.strip(),
        status="delivered"
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "status": "success",
        "message_id": msg.id,
        "incident_id": msg.incident_id,
        "sender_role": msg.sender_role,
        "sender_name": msg.sender_name,
        "message": msg.message,
        "created_at": msg.created_at.isoformat() if msg.created_at else None
    }

@router.get("/{incident_id}/messages")
def get_incident_messages(incident_id: str, db: Session = Depends(get_db)):
    """Fetch chronological message history for a specific emergency incident."""
    msgs = db.query(IncidentChatMessage).filter(
        IncidentChatMessage.incident_id == incident_id.strip()
    ).order_by(IncidentChatMessage.created_at.asc()).all()

    # Also lookup matching dispatch info if available
    dispatch = db.query(EmergencyDispatch).filter(EmergencyDispatch.cad_id == incident_id.strip()).first()
    dispatch_info = None
    if dispatch:
        dispatch_info = {
            "cad_id": dispatch.cad_id,
            "category": dispatch.category,
            "urgency": dispatch.urgency,
            "primary_agency": dispatch.primary_agency,
            "regional_helpline": dispatch.regional_helpline,
            "latitude": dispatch.latitude,
            "longitude": dispatch.longitude,
            "location_name": dispatch.location_name
        }

    return {
        "status": "success",
        "incident_id": incident_id,
        "dispatch_info": dispatch_info,
        "total_messages": len(msgs),
        "messages": [
            {
                "id": m.id,
                "sender_role": m.sender_role,
                "sender_name": m.sender_name,
                "message": m.message,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in msgs
        ]
    }

@router.get("/active-sessions")
def get_active_incident_sessions(db: Session = Depends(get_db)):
    """Lists all active citizen-authority incident sessions for the Authority Dashboard."""
    # Group messages by incident_id
    incident_ids = db.query(IncidentChatMessage.incident_id).distinct().all()
    sessions = []

    for (inc_id,) in incident_ids:
        last_msg = db.query(IncidentChatMessage).filter(
            IncidentChatMessage.incident_id == inc_id
        ).order_by(IncidentChatMessage.created_at.desc()).first()

        dispatch = db.query(EmergencyDispatch).filter(EmergencyDispatch.cad_id == inc_id).first()
        
        category = dispatch.category if dispatch else "Emergency SOS"
        urgency = dispatch.urgency if dispatch else "HIGH"
        location = dispatch.location_name if dispatch else "Coastal GPS"
        agency = dispatch.primary_agency if dispatch else "ERSS 112 Command"
        coords = f"{dispatch.latitude:.4f}, {dispatch.longitude:.4f}" if dispatch and dispatch.latitude else "Active"

        msg_count = db.query(IncidentChatMessage).filter(IncidentChatMessage.incident_id == inc_id).count()

        sessions.append({
            "incident_id": inc_id,
            "category": category,
            "urgency": urgency,
            "location": location,
            "coordinates": coords,
            "agency": agency,
            "total_messages": msg_count,
            "last_message": {
                "sender_role": last_msg.sender_role if last_msg else None,
                "sender_name": last_msg.sender_name if last_msg else None,
                "message": last_msg.message if last_msg else "",
                "created_at": last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None
            }
        })

    # Sort by most recent message
    sessions.sort(key=lambda s: s["last_message"]["created_at"] or "", reverse=True)

    return {
        "status": "success",
        "total_active_sessions": len(sessions),
        "sessions": sessions
    }
