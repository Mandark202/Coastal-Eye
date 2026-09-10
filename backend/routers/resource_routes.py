from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import ResourceCenter, ResourceAllocation
from ..resource_allocator import get_allocation_recommendations, dispatch_resource

router = APIRouter(prefix="/api/resource-allocation", tags=["Resource Allocation"])

class DispatchRequest(BaseModel):
    request_id: int
    resource_center_id: int
    resource: str
    quantity: int = 1

@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    """Fetch AI-optimized resource allocation recommendations."""
    recommendations = get_allocation_recommendations(db)
    return {"allocations": recommendations}

@router.post("/dispatch")
def dispatch(req: DispatchRequest, db: Session = Depends(get_db)):
    """Mark a resource as dispatched and update inventory."""
    success = dispatch_resource(db, req.request_id, req.resource_center_id, req.resource, req.quantity)
    if not success:
        raise HTTPException(status_code=400, detail="Dispatch failed. Check inventory or center ID.")
    return {"status": "success", "message": "Resource dispatched and tracked."}

@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """Fetch status of all resource centers."""
    centers = db.query(ResourceCenter).all()
    return centers
