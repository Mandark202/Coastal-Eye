import math
import heapq
from typing import List, Tuple, Dict
from .prediction_engine import get_predictions

def haversine_dist(lat1, lng1, lat2, lng2):
    # Returns distance in km
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_evacuation_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    # 1. Fetch risk zones to avoid
    predictions = get_predictions()
    risk_zones = predictions.get("zones", [])
    
    # 2. Setup A* Grid
    # We create a 20x20 grid around the bounding box of start/end
    min_lat = min(start_lat, end_lat) - 0.5
    max_lat = max(start_lat, end_lat) + 0.5
    min_lng = min(start_lng, end_lng) - 0.5
    max_lng = max(start_lng, end_lng) + 0.5
    
    rows, cols = 25, 25
    lat_step = (max_lat - min_lat) / rows
    lng_step = (max_lng - min_lng) / cols
    
    def to_grid(lat, lng):
        r = int((lat - min_lat) / lat_step)
        c = int((lng - min_lng) / lng_step)
        return max(0, min(rows-1, r)), max(0, min(cols-1, c))
    
    def from_grid(r, c):
        return min_lat + r * lat_step, min_lng + c * lng_step

    start_node = to_grid(start_lat, start_lng)
    end_node = to_grid(end_lat, end_lng)
    
    # 3. Cost Function
    def get_cost(r, c):
        lat, lng = from_grid(r, c)
        base_cost = 1.0 # unit distance
        risk_penalty = 0.0
        
        for zone in risk_zones:
            dist = math.sqrt((lat - zone["lat"])**2 + (lng - zone["lng"])**2)
            if dist < 0.3: # Proximity to risk zone
                # High penalty for high risk scores
                risk_penalty += (zone["risk_score"] / 10) * (1.0 - dist/0.3)
        
        # Check for "Blocked" routes (Extreme risk)
        if risk_penalty > 15:
            return float('inf')
            
        return base_cost + risk_penalty

    # 4. A* Algorithm
    pq = [(0, start_node)]
    g_score = {start_node: 0}
    came_from = {}
    
    while pq:
        current_f, current = heapq.heappop(pq)
        
        if current == end_node:
            break
            
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            neighbor = (current[0] + dr, current[1] + dc)
            if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols:
                move_cost = get_cost(neighbor[0], neighbor[1])
                if move_cost == float('inf'): continue
                
                # Diagonal move cost
                step_cost = 1.414 if dr != 0 and dc != 0 else 1.0
                tentative_g = g_score[current] + move_cost * step_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + math.sqrt((neighbor[0]-end_node[0])**2 + (neighbor[1]-end_node[1])**2)
                    heapq.heappush(pq, (f_score, neighbor))
                    came_from[neighbor] = current

    # 5. Reconstruct Path
    path = []
    curr = end_node
    if curr not in came_from and curr != start_node:
        # Fallback to direct path if A* fails due to blockages
        path = [[start_lat, start_lng], [end_lat, end_lng]]
    else:
        while curr in came_from:
            lat, lng = from_grid(curr[0], curr[1])
            path.append([lat, lng])
            curr = came_from[curr]
        path.append([start_lat, start_lng])
        path.reverse()
        # Add actual end point
        path[-1] = [end_lat, end_lng]

    # Calculate statistics
    total_dist = haversine_dist(start_lat, start_lng, end_lat, end_lng)
    
    # Determine overall risk level
    avg_risk_penalty = g_score.get(end_node, 0) / (len(path) or 1)
    risk_level = "Low"
    if avg_risk_penalty > 2.0: risk_level = "Moderate"
    if avg_risk_penalty > 4.0: risk_level = "High"

    time_mins = int((total_dist / 35.0) * 60) # 35km/h avg speed
    
    return {
        "route": path,
        "distance": f"{total_dist:.1f} km",
        "risk_level": risk_level,
        "estimated_time": f"{max(1, time_mins)} mins"
    }
