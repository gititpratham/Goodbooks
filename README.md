# SHELF/MATCH — Book Recommendation Service

**Author**: Suvidha Air  
**Submission For**: Recruitment Project 2026 — "Matching / Recommendation Service"  
**Deadline**: 8th July 2026  

## The "Why"
As per the Project 2026 requirements, this application fulfills the need for a **"Matching or suggestion-based application"** where users input their preferences, and the system matches their data against a catalog to provide multiple tailored results. 

Instead of a standard movie or dating app, this project implements a **Book Recommendation Engine** (SHELF/MATCH) based on the **Goodbooks-10K** dataset. It demonstrates the ability to handle large data relationships (10,000 books, 34,000+ tags, ~1 million tag linkages) and distill them into a responsive, intuitive interface.

## The "What"
**SHELF/MATCH** is a full-stack containerized web application that functions like a digital librarian:
1. **Intake Form**: Users select their preferred Genres, reading Moods, maximum Page Count, and Format.
2. **Recommendation Engine**: A custom Python backend cross-references these inputs against a curated SQLite database, applying a weighted ranking algorithm based on tag intersections, average rating, and popularity.
3. **Shortlist**: The user is presented with a personalized shortlist of book cards, highlighting their match percentage and the specific traits that aligned with their request.

### Technology Stack
- **Frontend**: React + TypeScript (Vite), styled with raw CSS for a bespoke, brutalist/editorial aesthetic.
- **Backend**: Python 3.11 with FastAPI and SQLite.
- **Infrastructure**: Fully Dockerized (multi-stage builds) and orchestrated with `docker-compose`.

## The "How" (Architecture & Logic)
The system is divided into two decoupled services communicating via a REST API:

### 1. Data Engineering & Backend (Python/FastAPI)
The core logic resides in `backend/recommender.py` and `backend/database.py`.
- **Seeding**: On first boot, the backend reads raw CSV files (`books_enriched.csv`, `tags.csv`, `book_tags.csv`) and seeds a WAL-mode SQLite database. The `book_tags` table contains nearly 1 million rows and is streamed in batches for memory efficiency.
- **Mapping**: User-friendly UI concepts (like the "Cozy" mood or "Sci-Fi" genre) are mapped under the hood to highly specific, community-driven Goodreads tags (e.g., "space-opera", "cyberpunk", "feel-good", "wholesome").
- **Scoring**: When a request is made, the backend performs SQL `LEFT JOIN` aggregations on the tag counts. Books are scored using a normalized formula:
  - 50% Genre match strength
  - 25% Mood match strength
  - 17% Quality (Average Rating)
  - 8% Popularity (Ratings Count)

### 2. Frontend (React/TypeScript)
The UI is a single-page React application served by Nginx.
- State is managed natively with React hooks (`useState`), collecting inputs across interactive tile components and range sliders.
- API requests are proxied through Nginx (`/api/recommend` -> `backend:8000`), avoiding CORS issues and ensuring a secure, production-ready architecture.
- The interface is fully responsive, prioritizing accessibility and immediate visual feedback.

---

## Running the Application (Plug and Play)

This project is configured to run instantly via Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Start the Services
1. Clone or extract the repository.
2. Open a terminal in the root directory (where `docker-compose.yml` is located).
3. Run the following command:
   ```bash
   docker-compose up --build
   ```
4. **Important**: On the very first run, the Python backend will spend ~30-60 seconds seeding the 1 million tag relationships into the SQLite database. The frontend is available immediately, but API requests will wait until the database is ready.
5. Open your browser and navigate to: **http://localhost**

### Stop the Services
```bash
docker-compose down
```
*(The SQLite database is stored in a persistent Docker volume, so subsequent startups will be instantaneous).*

## Directory Structure
- `/frontend`: React + TypeScript source code, Vite config, and Nginx setup.
- `/backend`: Python FastAPI source, Pydantic models, SQLite schema, and Recommender logic.
  - `/backend/db`: The raw Kaggle dataset CSVs used for seeding (`books.csv`, `tags.csv`, `book_tags.csv`).
- `/archive`: Old EDA notebooks, previous attempts, and project documents.