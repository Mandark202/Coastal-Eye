def estimate_cpi(alert_type: str):
    return {
        "Pollution": 90,
        "Cyclone": 40,
        "Weather": 50,
        "Illegal": 80
    }.get(alert_type, 30)
