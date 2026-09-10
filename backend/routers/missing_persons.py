"""
Missing Person / Family Reunification Router
============================================
Endpoints:
  POST   /missing-persons/report              — Report someone as missing
  GET    /missing-persons/search              — Search missing persons (name / location)
  GET    /missing-persons/{id}                — Get a specific missing-person record
  PATCH  /missing-persons/{id}/status         — Update status (Safe / Found / Missing)
  POST   /missing-persons/safe-declaration    — Self-declare as safe
  GET    /missing-persons/safe-declarations   — Search safety declarations
  POST   /shelter-checkins                    — Register someone at a shelter
  GET    /shelter-checkins/search             — Search shelter check-ins by name
  GET    /shelter-checkins/shelter/{sid}      — List everyone at a given shelter
  GET    /missing-persons-unified-search      — Search all three registries at once
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import MissingPerson, SafetyDeclaration, ShelterCheckin, ShelterFacility, get_ist_time

router = APIRouter(tags=["Missing Persons"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class MissingPersonCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = "Unknown"
    last_seen_location: str
    last_seen_lat: Optional[float] = None
    last_seen_lon: Optional[float] = None
    last_seen_at: Optional[str] = None   # ISO datetime string
    description: Optional[str] = ""
    photo_data: Optional[str] = None     # base64
    reporter_name: Optional[str] = "Anonymous"
    reporter_contact: Optional[str] = ""


class MissingPersonStatusUpdate(BaseModel):
    status: str  # Missing | Safe | Found


class SafetyDeclarationCreate(BaseModel):
    name: str
    age: Optional[int] = None
    current_location: str
    contact: Optional[str] = ""
    message: Optional[str] = ""


class ShelterCheckinCreate(BaseModel):
    shelter_id: Optional[int] = None
    shelter_name: Optional[str] = ""
    person_name: str
    age: Optional[int] = None
    gender: Optional[str] = "Unknown"
    notes: Optional[str] = ""
    reported_by: Optional[str] = "Shelter Staff"


# ─── Helper serialisers ───────────────────────────────────────────────────────

def _mp_to_dict(mp: MissingPerson) -> dict:
    return {
        "id": mp.id,
        "name": mp.name,
        "age": mp.age,
        "gender": mp.gender,
        "last_seen_location": mp.last_seen_location,
        "last_seen_lat": mp.last_seen_lat,
        "last_seen_lon": mp.last_seen_lon,
        "last_seen_at": mp.last_seen_at.isoformat() if mp.last_seen_at else None,
        "description": mp.description,
        "photo_data": mp.photo_data,
        "reporter_name": mp.reporter_name,
        "reporter_contact": mp.reporter_contact,
        "status": mp.status,
        "created_at": mp.created_at.isoformat() if mp.created_at else None,
        "updated_at": mp.updated_at.isoformat() if mp.updated_at else None,
        "record_type": "missing_person",
    }


def _sd_to_dict(sd: SafetyDeclaration) -> dict:
    return {
        "id": sd.id,
        "name": sd.name,
        "age": sd.age,
        "current_location": sd.current_location,
        "contact": sd.contact,
        "message": sd.message,
        "created_at": sd.created_at.isoformat() if sd.created_at else None,
        "status": "Safe",
        "record_type": "safety_declaration",
    }


def _sc_to_dict(sc: ShelterCheckin) -> dict:
    return {
        "id": sc.id,
        "shelter_id": sc.shelter_id,
        "shelter_name": sc.shelter_name,
        "person_name": sc.person_name,
        "age": sc.age,
        "gender": sc.gender,
        "notes": sc.notes,
        "reported_by": sc.reported_by,
        "checkin_time": sc.checkin_time.isoformat() if sc.checkin_time else None,
        "status": "Sheltered",
        "record_type": "shelter_checkin",
    }


# ─── Missing Person Endpoints ─────────────────────────────────────────────────

@router.post("/missing-persons/report", summary="Report a missing person")
def report_missing_person(data: MissingPersonCreate, db: Session = Depends(get_db)):
    last_seen_dt = None
    if data.last_seen_at:
        try:
            last_seen_dt = datetime.fromisoformat(data.last_seen_at)
        except ValueError:
            pass

    mp = MissingPerson(
        name=data.name,
        age=data.age,
        gender=data.gender,
        last_seen_location=data.last_seen_location,
        last_seen_lat=data.last_seen_lat,
        last_seen_lon=data.last_seen_lon,
        last_seen_at=last_seen_dt,
        description=data.description,
        photo_data=data.photo_data,
        reporter_name=data.reporter_name,
        reporter_contact=data.reporter_contact,
        status="Missing",
    )
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return {"success": True, "id": mp.id, "record": _mp_to_dict(mp)}


@router.get("/missing-persons/search", summary="Search missing persons by name or location")
def search_missing_persons(
    q: Optional[str] = Query(None, description="Name to search"),
    location: Optional[str] = Query(None, description="Location/area to filter by"),
    status: Optional[str] = Query(None, description="Missing | Safe | Found"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(MissingPerson)
    if q:
        query = query.filter(func.lower(MissingPerson.name).contains(q.lower()))
    if location:
        query = query.filter(func.lower(MissingPerson.last_seen_location).contains(location.lower()))
    if status:
        query = query.filter(MissingPerson.status == status)
    results = query.order_by(MissingPerson.created_at.desc()).limit(limit).all()
    return [_mp_to_dict(r) for r in results]


@router.get("/missing-persons/safe-declarations", summary="Search safety declarations")
def search_safety_declarations(
    q: Optional[str] = Query(None, description="Name to search"),
    location: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(SafetyDeclaration)
    if q:
        query = query.filter(func.lower(SafetyDeclaration.name).contains(q.lower()))
    if location:
        query = query.filter(func.lower(SafetyDeclaration.current_location).contains(location.lower()))
    results = query.order_by(SafetyDeclaration.created_at.desc()).limit(limit).all()
    return [_sd_to_dict(r) for r in results]


@router.get("/missing-persons/{person_id}", summary="Get a specific missing-person record")
def get_missing_person(person_id: int, db: Session = Depends(get_db)):
    mp = db.query(MissingPerson).filter(MissingPerson.id == person_id).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Record not found")
    return _mp_to_dict(mp)


@router.patch("/missing-persons/{person_id}/status", summary="Update status of a missing-person record")
def update_missing_person_status(
    person_id: int,
    data: MissingPersonStatusUpdate,
    db: Session = Depends(get_db),
):
    allowed = {"Missing", "Safe", "Found"}
    if data.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    mp = db.query(MissingPerson).filter(MissingPerson.id == person_id).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Record not found")
    mp.status = data.status
    mp.updated_at = get_ist_time()
    db.commit()
    db.refresh(mp)
    return {"success": True, "record": _mp_to_dict(mp)}


# ─── Safety Declaration Endpoints ────────────────────────────────────────────

@router.post("/missing-persons/safe-declaration", summary="Declare yourself as safe")
def declare_safe(data: SafetyDeclarationCreate, db: Session = Depends(get_db)):
    sd = SafetyDeclaration(
        name=data.name,
        age=data.age,
        current_location=data.current_location,
        contact=data.contact,
        message=data.message,
    )
    db.add(sd)
    db.commit()
    db.refresh(sd)
    return {"success": True, "id": sd.id, "record": _sd_to_dict(sd)}


# ─── Shelter Check-in Endpoints ──────────────────────────────────────────────

@router.post("/shelter-checkins", summary="Register someone at a cyclone shelter")
def shelter_checkin(data: ShelterCheckinCreate, db: Session = Depends(get_db)):
    shelter_name = data.shelter_name or ""
    if data.shelter_id and not shelter_name:
        shelter = db.query(ShelterFacility).filter(ShelterFacility.id == data.shelter_id).first()
        if shelter:
            shelter_name = shelter.name

    sc = ShelterCheckin(
        shelter_id=data.shelter_id,
        shelter_name=shelter_name,
        person_name=data.person_name,
        age=data.age,
        gender=data.gender,
        notes=data.notes,
        reported_by=data.reported_by,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return {"success": True, "id": sc.id, "record": _sc_to_dict(sc)}


@router.get("/shelter-checkins/search", summary="Search shelter check-ins by person name")
def search_shelter_checkins(
    q: Optional[str] = Query(None, description="Person name to search"),
    shelter_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ShelterCheckin)
    if q:
        query = query.filter(func.lower(ShelterCheckin.person_name).contains(q.lower()))
    if shelter_name:
        query = query.filter(func.lower(ShelterCheckin.shelter_name).contains(shelter_name.lower()))
    results = query.order_by(ShelterCheckin.checkin_time.desc()).limit(limit).all()
    return [_sc_to_dict(r) for r in results]


@router.get("/shelter-checkins/shelter/{shelter_id}", summary="List all check-ins at a given shelter")
def list_shelter_occupants(shelter_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(ShelterCheckin)
        .filter(ShelterCheckin.shelter_id == shelter_id)
        .order_by(ShelterCheckin.checkin_time.desc())
        .all()
    )
    return [_sc_to_dict(r) for r in results]


@router.get("/missing-persons-unified-search", summary="Search all three registries at once")
def unified_search(
    q: str = Query(..., description="Name to search across all registries"),
    location: Optional[str] = Query(None),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    """Searches MissingPersons, SafetyDeclarations, and ShelterCheckins by name."""
    q_lower = q.lower()

    mp_results = (
        db.query(MissingPerson)
        .filter(func.lower(MissingPerson.name).contains(q_lower))
        .order_by(MissingPerson.created_at.desc())
        .limit(limit)
        .all()
    )
    sd_results = (
        db.query(SafetyDeclaration)
        .filter(func.lower(SafetyDeclaration.name).contains(q_lower))
        .order_by(SafetyDeclaration.created_at.desc())
        .limit(limit)
        .all()
    )
    sc_results = (
        db.query(ShelterCheckin)
        .filter(func.lower(ShelterCheckin.person_name).contains(q_lower))
        .order_by(ShelterCheckin.checkin_time.desc())
        .limit(limit)
        .all()
    )

    combined = (
        [_mp_to_dict(r) for r in mp_results]
        + [_sd_to_dict(r) for r in sd_results]
        + [_sc_to_dict(r) for r in sc_results]
    )
    combined.sort(
        key=lambda x: x.get("created_at") or x.get("checkin_time") or "",
        reverse=True,
    )
    return combined[:limit]
