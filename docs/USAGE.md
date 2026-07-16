# Usage

## Using the Hosted Version

No installation is required to try the project — it's live on Oracle Cloud Infrastructure at:

👉 https://goodbooks.pratham.dpdns.org

## Using a Local Instance

Once the containers (or dev servers) are running, open:

- Frontend: `http://localhost:18080` (Docker) or `http://localhost:5173` (dev server)
- API docs: `http://localhost:18000/docs`

## Typical Workflow

1. Select preferred **genres** and **moods** using the tile filters.
2. Choose a **popularity** preference (`popular` or `underrated`).
3. Set a **minimum star rating** and a **maximum book runtime**.
4. Select an **era** (recent, classic, or any).
5. Submit the form — the app calls `POST /api/recommend` and the ML model returns your top 10
   matched books as cards, each with a match score, cover, author, genres, and description.

## Filter Defaults

Pre-selected when the page loads:

| Filter            | Default                     |
|-------------------|------------------------------|
| Genres            | Fantasy, Sci-Fi, Thriller    |
| Mood              | Cozy                         |
| Popularity        | Popular                      |
| Min Rating        | ★ 4.0                        |
| Max Book Runtime  | 30 hrs (≤ 1,500 pages)       |
| Era               | Recent (≥ 2000)              |

## Filters Explained

| Filter      | Field         | Behaviour |
|-------------|---------------|-----------|
| Genres      | `genres[]`    | Influences the genre multi-hot component of the preference vector |
| Mood        | `moods[]`     | Steers the ML score via the mood multi-hot encoding |
| Popularity  | `popularity`  | `popular` = no filter; `underrated` = excludes books with >65,000 ratings (top ~15%) |
| Min Rating  | `minRating`   | Hard filter — books below this average rating are excluded |
| Max Runtime | `maxPages`    | Hard filter on page count (50 pages/hour, e.g. 30 hrs = 1,500 pages) |
| Era         | `pubEra`      | `recent` = year ≥ 2000, `classic` = year < 1980, `any` = no filter |

## API Reference

Base URL (local): `http://localhost:18000` · Swagger docs: `http://localhost:18000/docs`

### `POST /api/recommend`

Request body:

```json
{
  "genres":     ["Fantasy", "Thriller"],
  "moods":      ["Cozy", "Escapist"],
  "minRating":  4.0,
  "maxPages":   1500,
  "pubEra":     "recent",
  "popularity": "popular"
}
```

Response:

```json
{
  "books": [
    {
      "title": "The Name of the Wind",
      "author": "Patrick Rothfuss",
      "genres": ["Fantasy", "Fiction"],
      "moods": [],
      "pitch": "A legendary figure recounts his life story...",
      "match": 92,
      "average_rating": 4.55,
      "ratings_count": 497765,
      "pages": 662,
      "image_url": "https://...",
      "pub_year": 2007
    }
  ],
  "count": 10,
  "query": { }
}
```

### `GET /api/health`
Returns backend health status and whether the database has been seeded.

### `GET /api/options/genres`
Returns available genre labels, sourced from the loaded ML model.

### `GET /api/options/moods`
Returns available mood labels, sourced from the loaded ML model.

## Retraining the Model

If `books_enriched.csv` is updated, or you want to retrain from scratch:

```bash
python archive/train_model.py
```

This loads `backend/db/books_enriched.csv` and `backend/db/ratings.csv`, builds training pairs
from all 53K users, trains and evaluates a new `MLPClassifier`, and saves the result to
`backend/model/recommender.joblib`.

Then rebuild the backend to pick up the new model:

```bash
docker compose build --no-cache backend && docker compose up -d backend
```

## Docs & Source

- Documentation / Source Code: https://github.com/gititpratham/Goodbooks
