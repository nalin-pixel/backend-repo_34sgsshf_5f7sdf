"""
Database Schemas for the Shove App

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Core domain schemas

class AppUser(BaseModel):
    """Users of the Shove app"""
    username: str = Field(..., min_length=3, max_length=32)
    segment: Optional[str] = Field(
        None,
        description="audience segment: teen, young-pro, enthusiast"
    )
    avatar: Optional[str] = Field(
        None,
        description="avatar type or URL"
    )
    city: Optional[str] = None
    country: Optional[str] = None

class PracticeSession(BaseModel):
    """Logs a single practice session for Shove."""
    user_id: str = Field(..., description="User identifier")
    duration_min: int = Field(..., ge=1, le=240)
    technique_score: int = Field(..., ge=0, le=100, description="self- or coach-rated score")
    attempts: int = Field(..., ge=1, le=500)
    notes: Optional[str] = Field(None, max_length=500)
    performed_at: Optional[datetime] = None

class Attempt(BaseModel):
    """A shared attempt media post (URL-based for simplicity)."""
    user_id: str
    media_url: str
    comment: Optional[str] = Field(None, max_length=300)
    technique_score: Optional[int] = Field(None, ge=0, le=100)

class Achievement(BaseModel):
    """Unlocked achievement document for a user."""
    user_id: str
    key: str
    title: str
    description: str
    icon: str
    unlocked_at: Optional[datetime] = None

# Tutorial step content (non-persistent schema for API response typing reference)
class TutorialStep(BaseModel):
    step: int
    title: str
    description: str
    tips: List[str]
    angle: str
    duration_sec: int
    speed_label: str
