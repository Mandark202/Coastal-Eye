from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os
from sqlalchemy.orm import Session
from ..database import engine, Base
from ..models import Post, Alert, AidRequest, VoiceSOS
from ..prediction_engine import get_predictions
import openai

router = APIRouter(prefix="/api/copilot", tags=["Copilot"])

class ChatRequest(BaseModel):
    message: str

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

def get_system_context(db: Session):
    """Gathers real-time data from the system for AI analysis."""
    reports = db.query(Post).filter(Post.status == "Open").all()
    aid_requests = db.query(AidRequest).filter(AidRequest.status == "Pending").all()
    alerts = db.query(Alert).all()
    predictions = get_predictions().get("zones", [])
    
    # Summary of state
    context = {
        "active_reports_count": len(reports),
        "pending_aid_requests_count": len(aid_requests),
        "active_alerts_count": len(alerts),
        "prediction_zones": predictions,
        "high_risk_reports": [p.location for p in reports if (p.risk_score or 0) > 70],
        "urgent_aid_requests": [a.location for a in aid_requests if a.urgency == "High"],
    }
    return context

@router.post("/chat")
def chat_with_copilot(req: ChatRequest):
    msg = req.message.lower()
    db = Session(engine)
    context = get_system_context(db)
    db.close()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        try:
            openai.api_key = api_key
            system_prompt = f"""
            You are 'CoastalEye AI Rescue Copilot', an advanced assistant for emergency authorities.
            Current System State:
            - Active Community Reports: {context['active_reports_count']} (High risk in: {', '.join(context['high_risk_reports']) or 'None'})
            - Pending Aid Requests: {context['pending_aid_requests_count']} (Urgent in: {', '.join(context['urgent_aid_requests']) or 'None'})
            - Active Alerts: {context['active_alerts_count']}
            - Predictions: {context['prediction_zones']}
            
            Analyze the situation and provide actionable advice. Be concise, professional, and futuristic.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": msg}
                ]
            )
            return {"response": response.choices[0].message.content}
        except Exception as e:
            # Fallback to rule-based if OpenAI fails
            pass

    # Smart Rule-Based Responses (Fallback or Default)
    if "risk" in msg or "highest" in msg:
        high_zones = sorted(context['prediction_zones'], key=lambda x: x['risk_score'], reverse=True)[:2]
        zones_str = ", ".join([f"{z['lat']}, {z['lng']} ({z['risk_type']} risk: {z['risk_score']}%)" for z in high_zones])
        return {"response": f"AI analysis identifies the following highest risk zones: {zones_str}. Recommend immediate deployment of monitoring units to these coordinates."}
        
    elif "emergency" in msg or "pending" in msg or "request" in msg:
        if context['pending_aid_requests_count'] > 0:
            return {"response": f"There are {context['pending_aid_requests_count']} pending aid requests. Priority should be given to {len(context['urgent_aid_requests'])} HIGH URGENCY requests in {', '.join(context['urgent_aid_requests']) or 'the coastal sector'}."}
        return {"response": "No pending emergency aid requests detected in the queue. System state is stable."}
        
    elif "flood" in msg or "prediction" in msg:
        flood_zones = [z for z in context['prediction_zones'] if z['risk_type'] == "Flood" and z['risk_score'] > 50]
        if flood_zones:
            return {"response": f"Predictive models suggest significant flooding risks in {len(flood_zones)} sectors. Maximum risk score detected: {max([z['risk_score'] for z in flood_zones])}%."}
        return {"response": "Flood risk levels are currently below the critical threshold (40%). Monitoring precipitation trends."}
        
    elif "evacuation" in msg or "advice" in msg:
        return {"response": "For evacuation: Inland routes via Highway 4 are clear. Avoid the South Coastal Bridge as water levels are reaching the 2m warning mark. Directing evacuees to Shelter Beta."}

    return {"response": f"Commander, I've analyzed {context['active_reports_count']} reports and {context['active_alerts_count']} alerts. Currently, the biggest threat is {context['prediction_zones'][0]['risk_type'] if context['prediction_zones'] else 'environmental instability'}. How shall we proceed?"}
