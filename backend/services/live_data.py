import requests
import datetime
from math import radians, sin, cos, sqrt, atan2

def fetch_weather_alerts(lat, lon):
    """
    Fetches real-time weather data from Open-Meteo and generates alerts based on thresholds.
    """
    alerts = []
    try:
        # Fetch current weather + forecast
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=precipitation,wave_height&daily=windspeed_10m_max&timezone=auto"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            current = data.get('current_weather', {})
            
            # 1. Wind Analysis
            wind_speed = current.get('windspeed', 0) # km/h
            if wind_speed > 60:
                alerts.append({
                    "title": "Severe Gale Warning",
                    "message": f"Dangerous wind speeds of {wind_speed} km/h detected. Avoid coastal areas.",
                    "severity": "High",
                    "type": "Cyclone",
                    "source": "Open-Meteo Weather API"
                })
            elif wind_speed > 40:
                alerts.append({
                    "title": "Strong Wind Advisory",
                    "message": f"High winds of {wind_speed} km/h. Small vessels should stay in port.",
                    "severity": "Medium",
                    "type": "Weather",
                    "source": "Open-Meteo Weather API"
                })
                
            # 2. Wave Height (if available in hourly for current hour)
            # Not always available for all coords, but let's try
            # (Simple heuristic if specific marine data isn't easily accessible without paid API)
            
    except Exception as e:
        print(f"Error fetching weather: {e}")
        
    return alerts

def fetch_earthquake_alerts(lat, lon, radius_km=1000):
    """
    Fetches recent significant earthquakes from USGS within a large radius.
    """
    alerts = []
    try:
        # USGS GeoJSON Feed (M2.5+ in last 24h) - Good balance
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            features = response.json().get('features', [])
            
            for f in features:
                props = f['properties']
                geo = f['geometry']['coordinates'] # lon, lat, depth
                
                eq_lon, eq_lat = geo[0], geo[1]
                mag = props.get('mag', 0)
                place = props.get('place', 'Unknown')
                
                # Calculate distance
                dist = haversine_distance(lat, lon, eq_lat, eq_lon)
                
                if dist < radius_km:
                    # Relevance check
                    severity = "Low"
                    if mag > 6.0: severity = "High"
                    elif mag > 4.5: severity = "Medium"
                    
                    # Create Alert
                    alerts.append({
                        "title": f"Earthquake - Magnitude {mag}",
                        "message": f"Detected {place}. Distance: {int(dist)}km.",
                        "severity": severity,
                        "type": "Tsunami" if mag > 6.5 and dist < 200 else "Earthquake",
                        "source": "USGS Real-time Feed",
                        "lat": eq_lat,
                        "lon": eq_lon
                    })
                    
    except Exception as e:
        print(f"Error fetching earthquakes: {e}")
        
    return alerts[:5] # Return top 5 nearest

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def get_real_time_alerts(lat, lon):
    """
    Aggregates alerts from all real-time providers.
    """
    weather = fetch_weather_alerts(lat, lon)
    quakes = fetch_earthquake_alerts(lat, lon)
    return weather + quakes
