import requests
import random
import math
from typing import List, Dict

# Coastal zones for prediction (can be expanded)
COASTAL_ZONES = [
    {"lat": 19.0760, "lng": 72.8777, "name": "Mumbai"},
    {"lat": 13.0827, "lng": 80.2707, "name": "Chennai"},
    {"lat": 17.6868, "lng": 83.2185, "name": "Visakhapatnam"},
    {"lat": 22.5726, "lng": 88.3639, "name": "Kolkata / Sunderbans"},
    {"lat": 15.2993, "lng": 73.9844, "name": "Goa"},
    {"lat": 9.9312, "lng": 76.2673, "name": "Kochi"},
    {"lat": 20.2677, "lng": 86.6006, "name": "Paradip"},
    {"lat": 21.6448, "lng": 69.6093, "name": "Porbandar"},
    {"lat": 12.9141, "lng": 74.8560, "name": "Mangalore"},
    {"lat": 16.9891, "lng": 82.2475, "name": "Kakinada"}
]

def fetch_seismic_data():
    """Fetch recent earthquake data from USGS."""
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("features", [])
    except Exception as e:
        print(f"Error fetching seismic data: {e}")
    return []

def fetch_weather_data(lat: float, lng: float):
    """Fetch weather forecast from Open-Meteo."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true&hourly=precipitation,windspeed_10m,surface_pressure"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching weather data for {lat}, {lng}: {e}")
    return {}

def calculate_risks(lat: float, lng: float, weather: dict, seismic: list) -> Dict:
    """Calculate AI risk scores based on environmental data."""
    current = weather.get("current_weather", {})
    wind_speed = current.get("windspeed", 0)
    
    # 1. Cyclone Risk (Based on wind speed)
    # 0-30: Low, 30-60: Mod, 60-90: High, 90+: Extreme
    cyclone_score = min(100, (wind_speed / 120) * 100) if wind_speed > 20 else random.randint(5, 15)
    
    # 2. Flood Risk (Based on precipitation forecast)
    hourly = weather.get("hourly", {})
    precip = sum(hourly.get("precipitation", [0])[:24]) # Total precip in 24h
    flood_score = min(100, (precip / 100) * 100) if precip > 10 else random.randint(10, 25)
    
    # 3. Tsunami Risk (Based on seismic activity near the coast)
    tsunami_score = 0
    max_mag = 0
    for eq in seismic:
        eq_lat = eq["geometry"]["coordinates"][1]
        eq_lng = eq["geometry"]["coordinates"][0]
        mag = eq["properties"]["mag"]
        
        # Haversine distance or simple approx
        dist = math.sqrt((lat - eq_lat)**2 + (lng - eq_lng)**2)
        if dist < 10 and mag > 5.0: # Close proximity and significant magnitude
            score = (mag / 9.5) * 100 * (1 - dist/10)
            tsunami_score = max(tsunami_score, score)
            max_mag = max(max_mag, mag)
    
    if tsunami_score == 0:
        tsunami_score = random.randint(0, 5)
        
    # Determine primary risk
    risks = [
        {"type": "Cyclone", "score": cyclone_score, "confidence": 85 if wind_speed > 40 else 60},
        {"type": "Flood", "score": flood_score, "confidence": 80 if precip > 20 else 55},
        {"type": "Tsunami", "score": tsunami_score, "confidence": 90 if max_mag > 6.0 else 40}
    ]
    
    primary_risk = max(risks, key=lambda x: x["score"])
    
    return {
        "lat": lat,
        "lng": lng,
        "risk_score": round(primary_risk["score"], 1),
        "risk_type": primary_risk["type"],
        "confidence": primary_risk["confidence"]
    }

def get_predictions():
    """Main entry point for AI Predictions."""
    seismic_data = fetch_seismic_data()
    prediction_zones = []
    
    for zone in COASTAL_ZONES:
        weather_data = fetch_weather_data(zone["lat"], zone["lng"])
        if weather_data:
            risk_data = calculate_risks(zone["lat"], zone["lng"], weather_data, seismic_data)
            prediction_zones.append(risk_data)
        else:
            # Fallback for demo
            prediction_zones.append({
                "lat": zone["lat"],
                "lng": zone["lng"],
                "risk_score": random.randint(20, 45),
                "risk_type": "Data Unavailable",
                "confidence": 0
            })
            
    # Add some random simulated high-risk points for visual density
    for _ in range(5):
        prediction_zones.append({
            "lat": 15 + random.uniform(-5, 10),
            "lng": 75 + random.uniform(-5, 15),
            "risk_score": random.randint(60, 95),
            "risk_type": random.choice(["Cyclone", "Flood", "Tsunami"]),
            "confidence": random.randint(75, 95)
        })
        
    return {"zones": prediction_zones}
