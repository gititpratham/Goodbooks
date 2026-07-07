"""
models.py — Pydantic request/response models for GOOD/BOOKS API
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    """Payload sent by the frontend intake form."""

    genres: List[str] = Field(default_factory=list, description="Selected genre labels")
    moods: List[str] = Field(default_factory=list, description="Selected mood labels")
    minRating: float = Field(default=3.5, ge=0.0, le=5.0, description="Minimum average rating filter")
    maxPages: int = Field(default=9999, ge=0, description="Maximum page count (9999 = no limit)")
    pubEra: str = Field(default="any", description="Publication era: 'recent' (>=2000), 'classic' (<1980), 'any'")
    popularity: str = Field(default="popular", description="Popularity preference: 'popular' or 'underrated'")


class BookResult(BaseModel):
    """Single book recommendation returned to the frontend."""

    title: str
    author: str
    genres: List[str]        # matched tag-based genres for display chips
    moods: List[str]         # matched mood labels for display chips
    pitch: str               # short description / pitch text
    match: int = Field(ge=0, le=100, description="Match percentage 0-100")
    average_rating: float
    ratings_count: int
    pages: Optional[int]
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
