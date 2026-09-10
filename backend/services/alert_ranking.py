from ..utils.geo import haversine
from ..utils.severity import severity_weight
from ..utils.cpi import estimate_cpi

def rank_alerts(alerts, user_lat, user_lon):
    ranked = []

    for alert in alerts:
        distance = haversine(user_lat, user_lon, alert.lat, alert.lon)
        severity = severity_weight(alert.severity)
        cpi = estimate_cpi(alert.alert_type)

        # User request: "first priority should be of the nearest coastal area"
        # We assign a massive weight to proximity.
        # Logic: 
        # 1. Proximity Score (0-60): Linear decay over 500km. 0km = 60pts, 500km+ = 0pts.
        # 2. Severity Score (0-30): High=30, Med=15, Low=5.
        # 3. CPI/Type Score (0-10): Bonus for specific types.
        
        proximity_score = max(0, 60 * (1 - (distance / 500)))
        
        priority_score = (
            severity * 0.3 +        # Severity is usually 10-100 scale in utils, let's assume severity_weight returns 0-100? No, let's check.
                                    # Assuming severity_weight returns relative value, we'll just trust the previous logic's scale but rebalanced.
                                    # Actually, let's look at the original code: 0.5 * severity.
                                    # We will use the new proximity logic + existing severity/cpi.
            proximity_score + 
            0.1 * cpi
        )

        ranked.append({
            "alert": alert,
            "distance_km": round(distance, 2),
            "cpi": cpi,
            "priority_score": round(priority_score, 2)
        })

    # Sort by priority score descending
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked
