from fastapi import APIRouter
from pydantic import BaseModel
from ..evacuation_engine import get_evacuation_route

router = APIRouter(prefix="/api", tags=["Evacuation"])

class EvacuationRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float

@router.post("/evacuation-route")
def fetch_evacuation_route(req: EvacuationRequest):
    return get_evacuation_route(req.start_lat, req.start_lng, req.end_lat, req.end_lng)
