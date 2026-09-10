from fastapi import APIRouter
from ..prediction_engine import get_predictions

router = APIRouter(prefix="/api", tags=["Predictions"])

@router.get("/predictions")
def fetch_predictions():
    return get_predictions()
