import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Post, FakeReportAnalysis

# Suspicious keywords that might indicate fake reports or spam
SUSPICIOUS_KEYWORDS = ["test", "fake", "prank", "joke", "troll", "ignore", "bot", "spam", "lol", "hahaha"]

def analyze_report_authenticity(db: Session, report_text: str, lat: float, lng: float, report_id: str = None) -> dict:
    """
    Analyzes a report for authenticity based on text, geolocation, and history.
    """
    text_lower = report_text.lower()
    
    # 1. Keyword Analysis
    flagged = [word for word in SUSPICIOUS_KEYWORDS if word in text_lower]
    keyword_score_penalty = len(flagged) * 20
    
    # 2. Duplicate Detection (Simplified for SQLite/Hackathon)
    # Check for identical text in the last 24 hours
    duplicate_count = db.query(Post).filter(
        Post.description == report_text,
        Post.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    duplicate_prob = min(100, duplicate_count * 25)
    
    # 3. Geolocation Validation (Simple boundary check)
    # Example: Check if it's within a reasonable range for India (approx 6-38 Lat, 68-98 Lng)
    # For coastal eye, we might be more specific. 
    geo_mismatch = not (6 <= lat <= 38 and 68 <= lng <= 98)
    geo_penalty = 40 if geo_mismatch else 0
    
    # 4. Spam/Frequency Analysis
    # (In a real app, check IP or user_id frequency)
    spam_prob = 0
    if len(report_text) < 10: # Too short
        spam_prob += 30
    if re.search(r'(.)\1{4,}', text_lower): # Repeated characters like "aaaaa"
        spam_prob += 40
        
    # 5. Final Authenticity Score Calculation
    # Start at 100, subtract penalties
    score = 100 - keyword_score_penalty - (duplicate_prob / 2) - geo_penalty - (spam_prob / 2)
    score = max(0, min(100, score))
    
    # Determine Trust Level
    if score >= 80:
        trust_level = "Trusted"
    elif score >= 50:
        trust_level = "Suspicious"
    else:
        trust_level = "Critical Review"
        
    analysis_result = {
        "report_id": report_id,
        "authenticity_score": int(score),
        "trust_level": trust_level,
        "duplicate_probability": int(duplicate_prob),
        "spam_probability": int(spam_prob),
        "geo_mismatch": geo_mismatch,
        "flagged_keywords": ",".join(flagged),
        "warnings": []
    }
    
    if geo_mismatch: analysis_result["warnings"].append("Impossible Geolocation")
    if duplicate_prob > 50: analysis_result["warnings"].append("Potential Duplicate")
    if len(flagged) > 0: analysis_result["warnings"].append(f"Suspicious Keywords: {analysis_result['flagged_keywords']}")
    
    # Save to DB if report_id is provided
    if report_id:
        new_analysis = FakeReportAnalysis(
            report_id=report_id,
            authenticity_score=analysis_result["authenticity_score"],
            trust_level=analysis_result["trust_level"],
            duplicate_probability=analysis_result["duplicate_probability"],
            spam_probability=analysis_result["spam_probability"],
            geo_mismatch=analysis_result["geo_mismatch"],
            flagged_keywords=analysis_result["flagged_keywords"]
        )
        db.add(new_analysis)
        db.commit()
        
    return analysis_result
