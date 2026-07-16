# Install

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
  (recommended path), **or**
- Python 3.11 and Node.js, if you'd rather run the backend and frontend without Docker.

## Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/gititpratham/Goodbooks.git
cd Goodbooks

# 2. Build and start all services
docker compose up --build

# if the above command fails to build the image, run:
sudo docker compose up --build
```

- Frontend → http://localhost:18080
- API Docs → http://localhost:18000/docs

On **first boot**, the backend automatically seeds the SQLite database from `backend/db/`. This
takes about 10–15 seconds. The database persists via a Docker volume (`goodbooks-data`), so
subsequent starts are instant.

### Rebuild a single service

```bash
docker compose build --no-cache frontend
docker compose up -d frontend
```

### Stop all containers

```bash
docker compose down
```

## Running without Docker

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 18000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
# Dev server starts at http://localhost:5173
```

## Notes

- The active production model ships at `backend/model/recommender.joblib` — no separate download
  step is needed to get recommendations working out of the box.
- To retrain the model yourself (e.g. after updating `books_enriched.csv`), see the **Usage**
  guide's *Retraining the Model* section.

For the most current and authoritative setup instructions, always refer to the repository README:
https://github.com/gititpratham/Goodbooks
