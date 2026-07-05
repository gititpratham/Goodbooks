"""
models.py — Pydantic request/response models for SHELF/MATCH API
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    """Payload sent by the frontend intake form."""

    genres: List[str] = Field(default_factory=list, description="Selected genre labels")
    moods: List[str] = Field(default_factory=list, description="Selected mood labels")
    maxPages: int = Field(default=900, ge=0, description="Maximum page count (900 = no limit)")
    format: str = Field(default="any", description="Preferred reading format")


class BookResult(BaseModel):
    """Single book recommendation returned to the frontend."""

    title: str
    author: str
    genres: List[str]
    moods: List[str]
    pages: Optional[int]
    formats: List[str]
    pitch: str
    match: int = Field(ge=0, le=100, description="Match percentage 0-100")
    average_rating: float
    ratings_count: int
    image_url: str
    pub_year: Optional[int]


class RecommendResponse(BaseModel):
    """Full API response from POST /api/recommend."""

    books: List[BookResult]
    count: int
    query: RecommendRequest


class HealthResponse(BaseModel):
    status: str
    service: str
    db_seeded: bool
    book_count: int
