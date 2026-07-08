# GOOD/BOOKS
## Installation Guide

**Version 1.0 | July 2026**

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation Method 1: Docker (Recommended)](#installation-method-1-docker-recommended)
4. [Installation Method 2: Manual Setup](#installation-method-2-manual-setup)
5. [Verifying the Installation](#verifying-the-installation)
6. [Retraining the Recommendation Model](#retraining-the-recommendation-model)
7. [Managing the Application](#managing-the-application)
8. [Troubleshooting](#troubleshooting)
9. [Appendix: Project Structure](#appendix-project-structure)

---

## Introduction

This guide walks you through installing and running **GOOD/BOOKS**, a full-stack, ML-powered book recommendation application built on the Goodbooks-10K dataset. It covers two supported installation paths — a containerized Docker setup (recommended for most users) and a manual, non-Docker setup for local development.

A live hosted version of the application is also available at **goodbooks.pratham.dpdns.org**, so installation is only necessary if you want to run, modify, or retrain the system yourself.

---

## System Requirements

| Requirement | Details |
|---|---|
| Operating System | Windows, macOS, or Linux |
| Docker Desktop | Required for the recommended installation path |
| Python | Version 3.11 (required only for the manual setup path) |
| Node.js / npm | Required only for the manual setup path (frontend build) |
| Disk Space | ~1 GB free (dataset, model artifacts, and container images) |
| Network Ports | `8080` (frontend) and `8000` (backend API) must be free |

---

## Installation Method 1: Docker (Recommended)

Docker packages the frontend, backend, and database into isolated, reproducible containers, so this is the fastest and most reliable way to get GOOD/BOOKS running.

### Step 1 — Install Docker Desktop

Download and install Docker Desktop from the [official website](https://www.docker.com/products/docker-desktop/), then confirm it is running before continuing.

### Step 2 — Clone the Repository

```bash
git clone https://github.com/gititpratham/Goodbooks.git
cd Goodbooks
```

### Step 3 — Build and Start the Containers

```bash
docker compose up --build
```

> **Note:** On some Linux distributions, Docker requires elevated permissions. If the command above fails to build the image, run:
> ```bash
> sudo docker compose up --build
> ```

### Step 4 — Access the Application

Once the containers finish starting, the application is available at:

| Service | URL |
|---|---|
| Frontend (Web App) | `http://localhost:8080` |
| Backend API Docs (Swagger) | `http://localhost:8000/docs` |

On the **first boot**, the backend automatically seeds the SQLite database from the files in `backend/db/`. This process takes approximately 10–15 seconds. The database is persisted in a named Docker volume (`goodbooks-data`), so subsequent restarts are instant.

---

## Installation Method 2: Manual Setup

Use this method if you prefer to run the frontend and backend directly on your machine without Docker — for example, during active development.

### Step 1 — Set Up the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will start on `http://localhost:8000`, with interactive documentation at `http://localhost:8000/docs`.

### Step 2 — Set Up the Frontend

Open a second terminal window:

```bash
cd frontend
npm install
npm run dev
```

The frontend development server will start on `http://localhost:5173`.

---

## Verifying the Installation

Once either installation method completes, confirm everything is working correctly:

1. Open `http://localhost:8000/api/health` (Docker) — you should receive a JSON response confirming the backend is healthy and the database is seeded.
2. Open the frontend URL in your browser (`http://localhost:8080` for Docker, or `http://localhost:5173` for manual setup).
3. Submit the preference form on the homepage and confirm that book recommendations are returned.

If any step fails, see [Troubleshooting](#troubleshooting) below.

---

## Retraining the Recommendation Model

The production model ships pre-trained, but you can retrain it — for example, after updating `books_enriched.csv`.

### Step 1 — Run the Training Script

```bash
python archive/train_model.py
```

This script will:

1. Load `backend/db/books_enriched.csv` and `backend/db/ratings.csv`.
2. Build training pairs from all ~53,000 users.
3. Train and evaluate a new MLP classifier.
4. Save the new model to `backend/model/recommender.joblib`.

### Step 2 — Rebuild the Backend Container

```bash
docker compose build --no-cache backend
docker compose up -d backend
```

This ensures the backend picks up the newly trained model file.

---

## Managing the Application

| Task | Command |
|---|---|
| Rebuild a single service (e.g. frontend) | `docker compose build --no-cache frontend` |
| Restart a service after rebuilding | `docker compose up -d frontend` |
| Stop all running containers | `docker compose down` |
| View live container logs | `docker compose logs -f` |

---

## Troubleshooting

| Issue | Likely Cause | Resolution |
|---|---|---|
| `docker compose up --build` fails to build | Insufficient permissions | Re-run the command with `sudo` |
| Port `8080` or `8000` already in use | Another process is bound to the port | Stop the conflicting process, or edit the port mapping in `docker-compose.yml` |
| Frontend loads but shows no recommendations | Backend not yet finished seeding the database | Wait 10–15 seconds after first boot, then refresh |
| Backend fails to start in manual setup | Missing dependencies | Re-run `pip install -r requirements.txt` inside the `backend` directory |
| Frontend fails to start in manual setup | Missing Node modules | Re-run `npm install` inside the `frontend` directory |
| Model retraining fails | Missing or malformed dataset files | Confirm `books_enriched.csv` and `ratings.csv` exist in `backend/db/` |

---

## Appendix: Project Structure

```
goodbooks/
├── docker-compose.yml          Orchestrates frontend + backend containers
├── README.md
│
├── backend/                    FastAPI application + ML engine
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 API entry point, route definitions
│   ├── models.py               Pydantic request/response models
│   ├── database.py             SQLite schema + seeding logic
│   ├── ml_recommender.py       MLBookRecommender inference class
│   ├── db/
│   │   ├── books_enriched.csv  10K books with genres, moods, pages
│   │   ├── tags.csv            Goodreads tag vocabulary
│   │   └── book_tags.csv       Book–tag association counts
│   └── model/
│       └── recommender.joblib  Active production model
│
├── frontend/                   React + TypeScript UI
│   ├── Dockerfile
│   ├── nginx.conf              Nginx reverse-proxy config
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx             Root component + form state
│       ├── constants.ts        Genre/mood lists + filter defaults
│       ├── types.ts            TypeScript interfaces (mirrors Pydantic)
│       ├── index.css           Global styles
│       ├── api/recommend.ts    API client (fetch wrapper)
│       └── components/         TileGroup, LengthSlider, RatingSlider, BookCard, etc.
│
└── archive/                    Development history (not used by the running app)
    ├── train_model.py          Model training script
    ├── recommender.py          Legacy SQL-based recommender
    ├── build_enriched.py       Builds books_enriched.csv from SQLite
    ├── goodbooks_eda.py        Exploratory Data Analysis
    ├── generate_descriptions.py Description generation utility
    └── eda/                    EDA output charts (PNG)
```

---

*GOOD/BOOKS — Installation Guide — Page generated for internal and end-user distribution.*
