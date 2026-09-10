from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..fake_detection import analyze_report_authenticity

router = APIRouter(prefix="/api/fake-detection", tags=["Fake Detection"])

class DetectionRequest(BaseModel):
    report_text: str
    latitude: float
    longitude: float

@router.post("/analyze")
def analyze_report(req: DetectionRequest, db: Session = Depends(get_db)):
    """
    Endpoint to manually trigger analysis or test the fake detection logic.
    """
    result = analyze_report_authenticity(
        db, 
        report_text=req.report_text, 
        lat=req.latitude, 
        lng=req.longitude
    )
    return result
