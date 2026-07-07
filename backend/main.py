from __future__ import annotations
import logging
import threading
import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import create_schema, get_connection, is_seeded, seed
from models import HealthResponse, RecommendRequest, RecommendResponse, BookResult
from ml_recommender import MLBookRecommender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("goodbooks")

_db_ready   = threading.Event()
_seed_error: str | None = None
ml_model = None

def _seed_worker() -> None:
    global _seed_error, ml_model
    try:
        conn = get_connection()
        create_schema(conn)
        if not is_seeded(conn):
            log.info("Database empty, seeding now (first run, ~10s)...")
            seed(conn)
        else:
            n = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
            log.info("Database already seeded (%d books). Ready.", n)
        conn.close()
        
        # Load ML model
        model_path = os.path.join(os.path.dirname(__file__), "model", "recommender.joblib")
        if os.path.exists(model_path):
            ml_model = MLBookRecommender(model_path)
            log.info("ML Recommender loaded successfully! ")
        else:
            log.warning(f"ML Recommender model not found at {model_path}.")
            
    except Exception as exc:
        _seed_error = str(exc)
        log.exception("Seeding or Model Loading failed: %s", exc)
    finally:
        _db_ready.set()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    t = threading.Thread(target=_seed_worker, daemon=True, name="seeder")
    t.start()
    yield


app = FastAPI(
    title="GOOD/BOOKS Recommendation API",
    version="2.0.0",
    description="Hybrid ML book recommendation engine built on Goodbooks-10K.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    try:
        conn    = get_connection()
        seeded  = is_seeded(conn)
        count   = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"] if seeded else 0
        conn.close()
    except Exception:
        seeded, count = False, 0
    return HealthResponse(status="ok", service="SHELF/MATCH API", db_seeded=seeded, book_count=count)


@app.post("/api/recommend", response_model=RecommendResponse, tags=["recommend"])
def recommend(req: RecommendRequest) -> RecommendResponse:
    if _seed_error:
        raise HTTPException(status_code=503, detail=f"Startup failed: {_seed_error}.")
    if not _db_ready.is_set():
        raise HTTPException(status_code=503, detail="System starting — retry in a moment.")
    if not ml_model:
        raise HTTPException(status_code=503, detail="ML model is not loaded yet.")

    try:
        raw_books = ml_model.recommend(
            genres=req.genres,
            moods=req.moods,
            min_rating=req.minRating,
            max_pages=None if req.maxPages >= 9999 else req.maxPages,
            year_pref=req.pubEra,
            popularity_pref=req.popularity,
            n=10
        )
        
        books = []
        for rb in raw_books:
            books.append(BookResult(
                title=rb["title"],
                author=rb["authors"],
                genres=eval(rb["genres"]) if isinstance(rb["genres"], str) and rb["genres"].startswith("[") else [],
                moods=[], # the ML model doesn't directly return matched moods without the explain() method, but we can just use req.moods for display if we want.
                pitch=rb["description"],
                match=int(max(50, min(100, rb["ml_score"] * 100))), # Convert 0-1 probability to percentage.
                average_rating=rb["average_rating"],
                ratings_count=rb["ratings_count"],
                pages=rb["pages"],
                image_url=rb["image_url"],
                pub_year=rb["pub_year"]
            ))
            
    except Exception as exc:
        log.exception("Recommendation error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RecommendResponse(books=books, count=len(books), query=req)

@app.get("/api/options/genres", response_model=List[str], tags=["options"])
def list_genres() -> List[str]:
    return ml_model.genre_list if ml_model else []

@app.get("/api/options/moods", response_model=List[str], tags=["options"])
def list_moods() -> List[str]:
    return ml_model.mood_list if ml_model else []
