def severity_weight(severity: str):
    return {
        "High": 100,
        "Medium": 60,
        "Low": 30
    }.get(severity, 20)
