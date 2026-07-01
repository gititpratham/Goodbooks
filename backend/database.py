import os
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/goodbooks")

# Setup SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for API routes to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def wait_for_db(max_retries=10, delay=3):
    """
    Waits for the database to become available before starting the application.
    This prevents container startup race conditions.
    """
    logger.info("Checking database connection...")
    for i in range(max_retries):
        try:
            # Try to connect and execute a simple test query
            conn = engine.connect()
            conn.execute(Base.metadata.clear())
            conn.close()
            logger.info("Database is ready!")
            return True
        except Exception as e:
            logger.warning(
                f"Database not ready yet (attempt {i+1}/{max_retries}). Error: {str(e)}"
            )
            time.sleep(delay)
    
    logger.error("Could not connect to the database. Exiting.")
    raise RuntimeError("Database connection timed out.")
