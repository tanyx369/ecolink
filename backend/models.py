from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NodeCreate(BaseModel):
    id: str
    type: str  # mentor | company | programme | partner
    name: str
    sectors: List[str] = []
    expertise_tags: List[str] = []
    country: str = "MY"
    city: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[str] = None


class EdgeCreate(BaseModel):
    id: str
    source: str
    target: str
    type: str  # MENTORS | ENROLLED | SUPPORTS | PAST_LINK
    fit_score: Optional[float] = None
    sessions_completed: Optional[int] = None
    outcome_rating: Optional[float] = None
    programme: Optional[str] = None
    status: str = "active"  # active | completed | pending | proposed
    reusable: bool = False


class EdgePatch(BaseModel):
    status: Optional[str] = None
    sessions_completed: Optional[int] = None
    outcome_rating: Optional[float] = None
    fit_score: Optional[float] = None


class MatchRequest(BaseModel):
    company_id: str
    programme_id: Optional[str] = None
