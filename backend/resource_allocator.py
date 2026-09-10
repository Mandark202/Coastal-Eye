import math
from sqlalchemy.orm import Session
from .models import AidRequest, ResourceCenter, ResourceAllocation, HospitalFacility, ShelterFacility

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine distance formula."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 9999.0
    R = 6371 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_optimal_hospital(req_lat: float, req_lng: float, hospitals: list) -> tuple:
    """Finds nearest hospital with available beds and trauma/ICU capability."""
    best_hosp = None
    min_dist = float('inf')
    for h in hospitals:
        if h.available_beds <= 0:
            continue # Skip completely saturated hospitals
        dist = calculate_distance(req_lat, req_lng, h.latitude, h.longitude)
        # Apply slight penalty if ICU is full but general beds exist
        effective_dist = dist + (5.0 if h.available_icu_beds <= 0 else 0.0)
        if effective_dist < min_dist:
            min_dist = dist
            best_hosp = h
    return best_hosp, min_dist

def find_optimal_shelter(req_lat: float, req_lng: float, shelters: list) -> tuple:
    """Finds nearest shelter with available capacity and potable water."""
    best_shelter = None
    min_dist = float('inf')
    for s in shelters:
        if s.available_capacity <= 0:
            continue # Skip full shelters
        dist = calculate_distance(req_lat, req_lng, s.latitude, s.longitude)
        # Apply penalty if food/water is depleted
        penalty = 0.0
        if s.food_status == "Depleted": penalty += 6.0
        if s.water_status == "Depleted": penalty += 8.0
        effective_dist = dist + penalty
        if effective_dist < min_dist:
            min_dist = dist
            best_shelter = s
    return best_shelter, min_dist

def get_allocation_recommendations(db: Session):
    """
    Analyzes pending aid requests and recommends optimal resource allocation
    factoring in live inventory, hospital beds, and shelter capacities.
    """
    # 1. Fetch pending requests (support both "Open" and "Pending")
    requests = db.query(AidRequest).filter(AidRequest.status.in_(["Open", "Pending"])).all()
    centers = db.query(ResourceCenter).all()
    hospitals = db.query(HospitalFacility).all()
    shelters = db.query(ShelterFacility).all()
    
    recommendations = []
    
    for req in requests:
        # Parse location if it's "lat, lng" or separate
        try:
            coords = req.location.split(",")
            req_lat = float(coords[0].strip())
            req_lng = float(coords[1].strip())
        except:
            # Fallback default coordinates if string name (e.g. Goa coast)
            req_lat, req_lng = 15.4989, 73.8278
            
        best_center = None
        min_dist = float('inf')
        
        # Find nearest resource center
        for center in centers:
            dist = calculate_distance(req_lat, req_lng, center.latitude, center.longitude)
            if dist < min_dist:
                min_dist = dist
                best_center = center
                
        if not best_center:
            continue
        
        need = (req.needs or "General").lower()
        resource_type = "Medical Kit"
        facility_info = None
        
        if "medical" in need or "ambulance" in need or "trauma" in need or "hospital" in need:
            resource_type = "Ambulance" if best_center.available_ambulances > 0 else "Medical Kit"
            hosp, h_dist = find_optimal_hospital(req_lat, req_lng, hospitals)
            if hosp:
                facility_info = {
                    "type": "Hospital",
                    "id": hosp.id,
                    "name": hosp.name,
                    "contact": hosp.contact_number,
                    "available_beds": hosp.available_beds,
                    "available_icu": hosp.available_icu_beds,
                    "oxygen_status": hosp.oxygen_status,
                    "distance": f"{h_dist:.1f} km",
                    "summary": f"{hosp.available_beds} beds free ({hosp.available_icu_beds} ICU open)"
                }
        elif "rescue" in need or "trapped" in need or "evac" in need or "shelter" in need:
            resource_type = "Rescue Boat" if best_center.available_rescue_boats > 0 else "Rescue Team"
            shlt, s_dist = find_optimal_shelter(req_lat, req_lng, shelters)
            if shlt:
                facility_info = {
                    "type": "Shelter",
                    "id": shlt.id,
                    "name": shlt.name,
                    "contact": shlt.contact_number,
                    "available_capacity": shlt.available_capacity,
                    "food_status": shlt.food_status,
                    "water_status": shlt.water_status,
                    "distance": f"{s_dist:.1f} km",
                    "summary": f"{shlt.available_capacity} slots open ({shlt.food_status} rations)"
                }
        elif "food" in need or "water" in need:
            resource_type = "Food Packets"
            shlt, s_dist = find_optimal_shelter(req_lat, req_lng, shelters)
            if shlt:
                facility_info = {
                    "type": "Shelter / Distribution Point",
                    "id": shlt.id,
                    "name": shlt.name,
                    "contact": shlt.contact_number,
                    "available_capacity": shlt.available_capacity,
                    "food_status": shlt.food_status,
                    "water_status": shlt.water_status,
                    "distance": f"{s_dist:.1f} km",
                    "summary": f"Distribution hub at {shlt.name}"
                }
            
        # Calculate Priority Score (0-100)
        urgency_weight = 0
        urg = (req.urgency or "Medium").capitalize()
        if "Crit" in urg or "High" in urg: urgency_weight = 60
        elif "Med" in urg: urgency_weight = 40
        else: urgency_weight = 20
        
        # Proximity bonus
        dist_bonus = max(0, 40 - (min_dist * 2)) 
        priority_score = min(100, urgency_weight + dist_bonus)
        
        user_display_name = req.user.name if (req.user and req.user.name) else f"Citizen #{req.id}"
        
        recommendations.append({
            "request_id": req.id,
            "user_name": user_display_name,
            "needs": req.needs or "General",
            "urgency": req.urgency or "Medium",
            "resource": resource_type,
            "priority_score": int(priority_score),
            "resource_center": best_center.name,
            "resource_center_id": best_center.id,
            "estimated_arrival": f"{int(min_dist * 4) + 4} mins",
            "distance": f"{min_dist:.1f} km",
            "recommended_facility": facility_info,
            "contact": req.contact or "112"
        })
        
    # Sort recommendations by priority score
    recommendations.sort(key=lambda x: x["priority_score"], reverse=True)
    return recommendations

def dispatch_resource(db: Session, request_id: int, center_id: int, resource: str, quantity: int):
    """
    Executes a dispatch by updating inventory and creating an allocation record.
    """
    center = db.query(ResourceCenter).filter(ResourceCenter.id == center_id).first()
    if not center:
        return False
    
    # Update Inventory
    if resource == "Ambulance": center.available_ambulances = max(0, center.available_ambulances - quantity)
    elif resource == "Medical Kit": center.available_medical_kits = max(0, center.available_medical_kits - quantity)
    elif resource == "Food Packets": center.available_food_packets = max(0, center.available_food_packets - quantity)
    elif resource == "Rescue Boat": center.available_rescue_boats = max(0, center.available_rescue_boats - quantity)
    
    # Update Aid Request status
    req = db.query(AidRequest).filter(AidRequest.id == request_id).first()
    if req:
        req.status = "In Progress"
        
    # Create Allocation Record
    new_alloc = ResourceAllocation(
        request_id=request_id,
        resource_center_id=center_id,
        allocated_resource=resource,
        quantity=quantity,
        priority_score=90,
        dispatch_status="Dispatched",
        estimated_arrival="12 mins"
    )
    
    db.add(new_alloc)
    db.commit()
    return True
