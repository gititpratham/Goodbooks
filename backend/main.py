"""
main.py — SHELF/MATCH FastAPI application entry point.

Run locally (from backend/ directory):
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Endpoints
---------
GET  /api/health          Health check + seeding status
POST /api/recommend       Main recommendation endpoint
GET  /api/options/genres  List available genre options
GET  /api/options/moods   List available mood options
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import create_schema, get_connection, is_seeded, seed
from models import BookResult, HealthResponse, RecommendRequest, RecommendResponse
from recommender import GENRE_TAG_MAP, MOOD_TAG_MAP, get_recommendations

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("shelfmatch")

# ── Shared state ──────────────────────────────────────────────────────────────
_db_ready = threading.Event()   # set once seeding finishes
_seed_error: str | None = None  # populated if seeding fails


# ── Lifespan ──────────────────────────────────────────────────────────────────

def _seed_worker() -> None:
    """Background thread: create schema + seed if needed."""
    global _seed_error
    try:
        conn = get_connection()
        create_schema(conn)
        if not is_seeded(conn):
            log.info("Database is empty — starting seed (may take 1–2 min on first run) …")
            seed(conn)
        else:
            n = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
            log.info("Database already seeded (%d books). Ready.", n)
        conn.close()
    except Exception as exc:
        _seed_error = str(exc)
        log.exception("Seeding failed: %s", exc)
    finally:
        _db_ready.set()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Kick off seeding in a daemon thread so the HTTP server starts immediately
    t = threading.Thread(target=_seed_worker, daemon=True, name="seeder")
    t.start()
    yield
    # shutdown — nothing to clean up for SQLite


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SHELF/MATCH — Book Recommendation API",
    version="1.0.0",
    description="Hybrid tag-based book recommendation engine built on Goodbooks-10K.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Nginx proxy handles origins in production
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Quick health check that reports DB seeding status."""
    try:
        conn = get_connection()
        seeded = is_seeded(conn)
        count  = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"] if seeded else 0
        conn.close()
    except Exception:
        seeded, count = False, 0

    return HealthResponse(
        status="ok",
        service="SHELF/MATCH API",
        db_seeded=seeded,
        book_count=count,
    )


@app.post("/api/recommend", response_model=RecommendResponse, tags=["recommend"])
def recommend(req: RecommendRequest) -> RecommendResponse:
    """
    Return up to 12 book recommendations ranked by match score.

    The score weights are:
    - Genre tag match  50 %
    - Mood  tag match  25 %
    - Rating quality   17 %
    - Popularity        8 %
    """
    if _seed_error:
        raise HTTPException(status_code=503, detail=f"Database seeding failed: {_seed_error}")

    if not _db_ready.is_set():
        raise HTTPException(
            status_code=503,
            detail="Database is being seeded — please try again in a moment.",
        )

    try:
        conn   = get_connection()
        books  = get_recommendations(conn, req)
        conn.close()
    except Exception as exc:
        log.exception("Recommendation error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RecommendResponse(books=books, count=len(books), query=req)


@app.get("/api/options/genres", response_model=List[str], tags=["options"])
def list_genres() -> List[str]:
    """Return the available genre options for the intake form."""
    return list(GENRE_TAG_MAP.keys())


@app.get("/api/options/moods", response_model=List[str], tags=["options"])
def list_moods() -> List[str]:
    """Return the available mood options for the intake form."""
    return list(MOOD_TAG_MAP.keys())
