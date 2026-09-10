from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Post, User, Comment
from ..ai_logic import calculate_risk_score
from pydantic import BaseModel
from typing import Optional, List
import uuid

router = APIRouter(tags=["Posts"])

class PostCreate(BaseModel):
    user_id: int
    location: str
    caption: str
    description: str
    image_data: str # Base64

class CommentCreate(BaseModel):
    user_id: int
    text: str

@router.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    from ..models import FakeReportAnalysis
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    # Serialize manually or use Pydantic schema response_model
    # For speed, doing a quick dict conversion including user name
    result = []
    for p in posts:
        analysis = db.query(FakeReportAnalysis).filter(FakeReportAnalysis.report_id == p.id).first()
        
        result.append({
            "id": p.id,
            "owner": p.owner.name if p.owner else "Unknown",
            "owner_id": p.user_id,
            "location": p.location,
            "caption": p.caption,
            "description": p.description,
            "imageData": p.image_data,
            "likes": p.likes,
            "createdAt": p.created_at.isoformat(),
            "comments": [{"text": c.text, "at": c.created_at.isoformat()} for c in p.comments],
            "ai_verification": {
                "trust_level": analysis.trust_level if analysis else "Trusted",
                "score": analysis.authenticity_score if analysis else 100
            }
        })
    return result

@router.post("/posts")
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    # Calculate Risk Score (AI)
    risk = calculate_risk_score(post.caption + " " + post.description, post.location)
    
    new_post = Post(
        id="p_" + str(uuid.uuid4().hex[:8]),
        user_id=post.user_id,
        location=post.location,
        caption=post.caption,
        description=post.description,
        image_data=post.image_data,
        risk_score=risk
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # AI Fake Detection Trigger
    from ..fake_detection import analyze_report_authenticity
    # Try to parse lat/lng from location string if it's "lat, lng" format
    try:
        coords = post.location.split(",")
        lat = float(coords[0].strip())
        lng = float(coords[1].strip())
    except:
        lat, lng = 0.0, 0.0 # Default if location is just a name
        
    analyze_report_authenticity(db, post.description, lat, lng, report_id=new_post.id)
    
    return {"message": "Post created", "post_id": new_post.id, "risk_score": risk}

@router.post("/posts/{post_id}/like")
def like_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.likes += 1
    db.commit()
    return {"likes": post.likes}

@router.post("/posts/{post_id}/comment")
def add_comment(post_id: str, comment: CommentCreate, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    new_comment = Comment(
        text=comment.text,
        post_id=post_id
        # In a real app, link to user_id too
    )
    db.add(new_comment)
    db.commit()
    return {"message": "Comment added"}
