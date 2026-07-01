import os
import ast
import logging
from contextlib import asynccontextmanager
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import wait_for_db, get_db, Base, engine, SessionLocal
from models import Book
from recommender import BookRecommender

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Recommender Instance
recommender = BookRecommender()

def seed_database(db: Session):
    """
    Seeds the database with books from the books_enriched.csv file if the books table is empty.
    Uses pandas for fast parsing and batch inserts to PostgreSQL.
    """
    try:
        book_count = db.query(Book).count()
        if book_count > 0:
            logger.info(f"Database already contains {book_count} books. Seeding skipped.")
            return

        csv_path = os.path.join(os.path.dirname(__file__), "data", "books_enriched.csv")
        logger.info(f"Seeding database from CSV: {csv_path}")
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found at {csv_path}!")
            return

        # Load CSV using pandas
        df = pd.read_csv(csv_path)
        # Drop duplicates on book_id
        df = df.drop_duplicates(subset=["book_id"])
        
        # Fill NaN values with defaults
        df["title"] = df["title"].fillna(df["original_title"]).fillna("Unknown Title")
        df["authors"] = df["authors"].fillna("[]")
        df["average_rating"] = df["average_rating"].fillna(0.0)
        df["description"] = df["description"].fillna("")
        df["genres"] = df["genres"].fillna("[]")
        df["image_url"] = df["image_url"].fillna("")
        df["pages"] = df["pages"].fillna(0).astype(int)
        df["publishDate"] = df["publishDate"].fillna("Unknown")
        df["ratings_count"] = df["ratings_count"].fillna(0).astype(int)

        books_to_insert = []
        for _, row in df.iterrows():
            book = Book(
                book_id=int(row["book_id"]),
                title=str(row["title"]),
                authors=str(row["authors"]),
                average_rating=float(row["average_rating"]),
                description=str(row["description"]),
                genres=str(row["genres"]),
                image_url=str(row["image_url"]),
                pages=int(row["pages"]),
                publish_date=str(row["publishDate"]),
                ratings_count=int(row["ratings_count"])
            )
            books_to_insert.append(book)

        # Batch insert using SQLAlchemy
        logger.info(f"Inserting {len(books_to_insert)} records into PostgreSQL...")
        batch_size = 1000
        for i in range(0, len(books_to_insert), batch_size):
            db.bulk_save_objects(books_to_insert[i:i+batch_size])
            db.commit()
            logger.info(f"Inserted batch {i // batch_size + 1}")
            
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager.
    Handles startup sequence: Wait for DB -> Init tables -> Seed DB -> Fit Recommender.
    """
    logger.info("Starting up Book Recommendation Service...")
    # 1. Wait for database connection
    wait_for_db()
    
    # 2. Create tables
    Base.metadata.create_all(bind=engine)
    
    # 3. Seed database
    db = SessionLocal()
    try:
        seed_database(db)
        
        # 4. Fetch all books from DB and fit recommender
        logger.info("Loading books from database into recommender...")
        books = db.query(Book).all()
        books_dicts = [b.to_dict() for b in books]
        recommender.fit(books_dicts)
    finally:
        db.close()
        
    yield
    logger.info("Shutting down Book Recommendation Service...")

app = FastAPI(
    title="Book Recommendation API",
    description="A content-based book recommendation service using TF-IDF and Cosine Similarity.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas for requests
class BookRecommendRequest(BaseModel):
    book_id: int = Field(..., description="ID of the book to get recommendations for")
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations to return")

class PreferenceRecommendRequest(BaseModel):
    genres: list[str] = Field(default=[], description="List of preferred genres")
    keywords: str = Field(default="", description="Keywords, tags, or mood keywords")
    min_rating: float = Field(0.0, ge=0.0, le=5.0, description="Minimum average rating")
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations to return")

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/api/genres", tags=["Books"])
def get_genres(db: Session = Depends(get_db)):
    """Extracts and returns a unique sorted list of all genres in the database."""
    books = db.query(Book.genres).all()
    unique_genres = set()
    for row in books:
        if row[0]:
            try:
                # Convert string list e.g. "['fiction', 'fantasy']" to python list
                genres_list = ast.literal_eval(row[0])
                if isinstance(genres_list, list):
                    for genre in genres_list:
                        unique_genres.add(genre.strip().title())
            except Exception:
                continue
    return sorted(list(unique_genres))

@app.get("/api/books", tags=["Books"])
def list_books(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by title or authors"),
    genre: str = Query("", description="Filter by genre"),
    db: Session = Depends(get_db)
):
    """Retrieves a paginated, filterable list of books from the catalog."""
    query = db.query(Book)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Book.title.ilike(search_filter) | Book.authors.ilike(search_filter)
        )
        
    if genre:
        genre_filter = f"%'{genre.lower()}'%"
        query = query.filter(Book.genres.ilike(genre_filter))
        
    total_count = query.count()
    
    # Sort by ratings count (popularity) as default
    query = query.order_by(Book.ratings_count.desc())
    
    offset = (page - 1) * limit
    books = query.offset(offset).limit(limit).all()
    
    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "books": [b.to_dict() for b in books]
    }

@app.get("/api/books/{book_id}", tags=["Books"])
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Retrieves details of a single book by its ID."""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found."
        )
    return book.to_dict()

@app.post("/api/recommend/by-book", tags=["Recommendations"])
def recommend_by_book(request: BookRecommendRequest):
    """
    Returns content-based recommendations for a specific book.
    """
    recommendations = recommender.get_recommendations_by_book(
        book_id=request.book_id,
        limit=request.limit
    )
    return {"recommendations": recommendations}

@app.post("/api/recommend/by-preferences", tags=["Recommendations"])
def recommend_by_preferences(request: PreferenceRecommendRequest):
    """
    Matches user-selected preferences (genres, keywords, minimum rating) to return recommendations.
    """
    recommendations = recommender.get_recommendations_by_preferences(
        genres=request.genres,
        keywords=request.keywords,
        min_rating=request.min_rating,
        limit=request.limit
    )
    return {"recommendations": recommendations}
