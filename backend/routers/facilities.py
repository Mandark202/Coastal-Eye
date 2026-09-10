from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import HospitalFacility, ShelterFacility

router = APIRouter(prefix="/api/facilities", tags=["Facilities & Capacity"])

class HospitalUpdate(BaseModel):
    occupied_beds: Optional[int] = None
    total_beds: Optional[int] = None
    icu_beds_occupied: Optional[int] = None
    icu_beds_total: Optional[int] = None
    oxygen_status: Optional[str] = None # Sufficient, Moderate, Critical

class ShelterUpdate(BaseModel):
    current_occupancy: Optional[int] = None
    total_capacity: Optional[int] = None
    food_status: Optional[str] = None # Full, Moderate, Depleted
    water_status: Optional[str] = None # Potable Available, Limited, Depleted
    generator_power: Optional[bool] = None

# Initial Coastal Hospital & Shelter Seed Data
INITIAL_HOSPITALS = [
    {
        "name": "Goa Medical College & Hospital (Bambolim)",
        "latitude": 15.4607, "longitude": 73.8567, "zone": "Goa Coastal",
        "contact_number": "+91 832 2458700", "total_beds": 120, "occupied_beds": 78,
        "icu_beds_total": 24, "icu_beds_occupied": 16, "oxygen_status": "Sufficient", "trauma_center": True
    },
    {
        "name": "North Goa District Hospital (Mapusa)",
        "latitude": 15.5925, "longitude": 73.8152, "zone": "Goa North",
        "contact_number": "+91 832 2262211", "total_beds": 80, "occupied_beds": 42,
        "icu_beds_total": 12, "icu_beds_occupied": 5, "oxygen_status": "Sufficient", "trauma_center": True
    },
    {
        "name": "KEM Hospital & Trauma Center (Mumbai)",
        "latitude": 19.0024, "longitude": 72.8427, "zone": "Mumbai Coastal",
        "contact_number": "+91 22 24107000", "total_beds": 250, "occupied_beds": 215,
        "icu_beds_total": 45, "icu_beds_occupied": 41, "oxygen_status": "Moderate", "trauma_center": True
    },
    {
        "name": "Rajiv Gandhi Government General Hospital (Chennai)",
        "latitude": 13.0805, "longitude": 80.2785, "zone": "Chennai Harbor",
        "contact_number": "+91 44 25305000", "total_beds": 200, "occupied_beds": 140,
        "icu_beds_total": 35, "icu_beds_occupied": 22, "oxygen_status": "Sufficient", "trauma_center": True
    },
    {
        "name": "Ernakulam General Hospital (Kochi)",
        "latitude": 9.9723, "longitude": 76.2829, "zone": "Kerala Coast",
        "contact_number": "+91 484 2361251", "total_beds": 150, "occupied_beds": 95,
        "icu_beds_total": 20, "icu_beds_occupied": 11, "oxygen_status": "Sufficient", "trauma_center": True
    },
    {
        "name": "District Headquarters Hospital (Puri, Odisha)",
        "latitude": 19.8135, "longitude": 85.8312, "zone": "Odisha Coastal",
        "contact_number": "+91 6752 222045", "total_beds": 100, "occupied_beds": 65,
        "icu_beds_total": 15, "icu_beds_occupied": 9, "oxygen_status": "Sufficient", "trauma_center": True
    }
]

INITIAL_SHELTERS = [
    {
        "name": "Morjim Multipurpose Cyclone Shelter",
        "latitude": 15.6186, "longitude": 73.7410, "zone": "Goa North",
        "contact_number": "1070", "total_capacity": 600, "current_occupancy": 180,
        "food_status": "Full", "water_status": "Potable Available", "generator_power": True
    },
    {
        "name": "Calangute Community Safe Shelter",
        "latitude": 15.5439, "longitude": 73.7553, "zone": "Goa Coastal",
        "contact_number": "1070", "total_capacity": 450, "current_occupancy": 320,
        "food_status": "Moderate", "water_status": "Potable Available", "generator_power": True
    },
    {
        "name": "Bandra Reclamation Emergency Relief Camp",
        "latitude": 19.0435, "longitude": 72.8256, "zone": "Mumbai Coastal",
        "contact_number": "1916", "total_capacity": 1200, "current_occupancy": 840,
        "food_status": "Full", "water_status": "Potable Available", "generator_power": True
    },
    {
        "name": "Marina Beach Tsunami Relief Center",
        "latitude": 13.0489, "longitude": 80.2825, "zone": "Chennai Coast",
        "contact_number": "1070", "total_capacity": 800, "current_occupancy": 410,
        "food_status": "Full", "water_status": "Potable Available", "generator_power": True
    },
    {
        "name": "Fort Kochi Coastal Evacuation Haven",
        "latitude": 9.9658, "longitude": 76.2421, "zone": "Kerala Coast",
        "contact_number": "1079", "total_capacity": 500, "current_occupancy": 150,
        "food_status": "Full", "water_status": "Potable Available", "generator_power": True
    },
    {
        "name": "Puri OSDMA Super Cyclone Shelter",
        "latitude": 19.7983, "longitude": 85.8249, "zone": "Odisha Coastal",
        "contact_number": "1070", "total_capacity": 1500, "current_occupancy": 650,
        "food_status": "Full", "water_status": "Potable Available", "generator_power": True
    }
]

def seed_facilities_if_empty(db: Session):
    """Populates initial coastal hospital and shelter records if not present."""
    if db.query(HospitalFacility).count() == 0:
        for h in INITIAL_HOSPITALS:
            db.add(HospitalFacility(**h))
        db.commit()

    if db.query(ShelterFacility).count() == 0:
        for s in INITIAL_SHELTERS:
            db.add(ShelterFacility(**s))
        db.commit()

@router.get("/capacity")
def get_facilities_capacity(db: Session = Depends(get_db)):
    """Fetch live bed counts, ICU utilization, and shelter occupancy across all coastal zones."""
    seed_facilities_if_empty(db)
    
    hospitals = db.query(HospitalFacility).all()
    shelters = db.query(ShelterFacility).all()

    total_beds = sum(h.total_beds for h in hospitals)
    occupied_beds = sum(h.occupied_beds for h in hospitals)
    available_beds = max(0, total_beds - occupied_beds)

    total_icu = sum(h.icu_beds_total for h in hospitals)
    occupied_icu = sum(h.icu_beds_occupied for h in hospitals)
    available_icu = max(0, total_icu - occupied_icu)

    total_shelter_cap = sum(s.total_capacity for s in shelters)
    shelter_occupancy = sum(s.current_occupancy for s in shelters)
    available_shelter_cap = max(0, total_shelter_cap - shelter_occupancy)

    return {
        "status": "success",
        "summary": {
            "total_hospitals": len(hospitals),
            "total_shelters": len(shelters),
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "bed_occupancy_rate": round((occupied_beds / max(1, total_beds)) * 100, 1),
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "total_shelter_capacity": total_shelter_cap,
            "current_shelter_occupancy": shelter_occupancy,
            "available_shelter_capacity": available_shelter_cap,
            "shelter_occupancy_rate": round((shelter_occupancy / max(1, total_shelter_cap)) * 100, 1)
        },
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "zone": h.zone,
                "contact_number": h.contact_number,
                "total_beds": h.total_beds,
                "occupied_beds": h.occupied_beds,
                "available_beds": h.available_beds,
                "icu_beds_total": h.icu_beds_total,
                "icu_beds_occupied": h.icu_beds_occupied,
                "available_icu_beds": h.available_icu_beds,
                "occupancy_rate": h.occupancy_rate,
                "oxygen_status": h.oxygen_status,
                "trauma_center": h.trauma_center,
                "is_full": h.available_beds == 0
            } for h in hospitals
        ],
        "shelters": [
            {
                "id": s.id,
                "name": s.name,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "zone": s.zone,
                "contact_number": s.contact_number,
                "total_capacity": s.total_capacity,
                "current_occupancy": s.current_occupancy,
                "available_capacity": s.available_capacity,
                "occupancy_rate": s.occupancy_rate,
                "food_status": s.food_status,
                "water_status": s.water_status,
                "generator_power": s.generator_power,
                "is_full": s.available_capacity == 0
            } for s in shelters
        ]
    }

@router.post("/hospital/{hospital_id}/update")
def update_hospital_capacity(hospital_id: int, req: HospitalUpdate, db: Session = Depends(get_db)):
    """Update live hospital bed count, ICU occupancy, or oxygen status."""
    hospital = db.query(HospitalFacility).filter(HospitalFacility.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if req.occupied_beds is not None:
        hospital.occupied_beds = max(0, min(hospital.total_beds, req.occupied_beds))
    if req.total_beds is not None:
        hospital.total_beds = max(1, req.total_beds)
    if req.icu_beds_occupied is not None:
        hospital.icu_beds_occupied = max(0, min(hospital.icu_beds_total, req.icu_beds_occupied))
    if req.icu_beds_total is not None:
        hospital.icu_beds_total = max(1, req.icu_beds_total)
    if req.oxygen_status is not None:
        hospital.oxygen_status = req.oxygen_status

    db.commit()
    db.refresh(hospital)
    return {
        "status": "success",
        "message": f"Updated capacity for {hospital.name}",
        "available_beds": hospital.available_beds,
        "available_icu_beds": hospital.available_icu_beds,
        "occupancy_rate": hospital.occupancy_rate
    }

@router.post("/shelter/{shelter_id}/update")
def update_shelter_capacity(shelter_id: int, req: ShelterUpdate, db: Session = Depends(get_db)):
    """Update live shelter occupancy or food/water status."""
    shelter = db.query(ShelterFacility).filter(ShelterFacility.id == shelter_id).first()
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found")

    if req.current_occupancy is not None:
        shelter.current_occupancy = max(0, min(shelter.total_capacity, req.current_occupancy))
    if req.total_capacity is not None:
        shelter.total_capacity = max(1, req.total_capacity)
    if req.food_status is not None:
        shelter.food_status = req.food_status
    if req.water_status is not None:
        shelter.water_status = req.water_status
    if req.generator_power is not None:
        shelter.generator_power = req.generator_power

    db.commit()
    db.refresh(shelter)
    return {
        "status": "success",
        "message": f"Updated capacity for {shelter.name}",
        "available_capacity": shelter.available_capacity,
        "occupancy_rate": shelter.occupancy_rate
    }
