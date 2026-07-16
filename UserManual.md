# GOOD/BOOKS
## User Manual

**Version 1.0 | July 2026**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Accessing the Application](#accessing-the-application)
3. [How Recommendations Work](#how-recommendations-work)
4. [Using the Web Interface](#using-the-web-interface)
5. [Understanding the Filters](#understanding-the-filters)
6. [Reading Your Recommendations](#reading-your-recommendations)
7. [Default Preferences](#default-preferences)
8. [API Reference (For Developers)](#api-reference-for-developers)
9. [System Architecture Overview](#system-architecture-overview)
10. [Dataset Information](#dataset-information)
11. [Frequently Asked Questions](#frequently-asked-questions)

---

## Introduction

**GOOD/BOOKS** is a personalized book recommendation web application. It asks users a short series of questions about their reading preferences — genres, mood, popularity, rating threshold, book length, and era — and returns a curated list of the ten books best matched to those preferences, powered by a trained machine learning model.

This manual explains how to use the application from an end-user perspective: how the form works, what each filter does, and how to interpret your results.

---

## Accessing the Application

GOOD/BOOKS can be accessed in two ways:

| Access Method | Location |
|---|---|
| **Live Demo** | [goodbooks.pratham.dpdns.org](https://goodbooks.pratham.dpdns.org) |
| **Self-Hosted** | `http://localhost:18080` after a local installation (see the *Installation Guide*) |

No account or sign-up is required — recommendations are generated instantly from the preferences you select on the page.

---

## How Recommendations Work

Behind the scenes, GOOD/BOOKS uses a **hybrid machine learning system** to generate its recommendations:

- A **Multi-Layer Perceptron (MLP)** neural network, trained on more than 424,000 pairwise user–book interactions drawn from over 53,000 real readers.
- **TF-IDF and SVD** description embeddings, which give the model a semantic understanding of what each book is actually about.
- **Genre and mood encoding**, which aligns recommendations with the tone and category of book you're in the mood for.
- **Hard filters**, which strictly enforce your rating, length, era, and popularity preferences before anything is ranked.

In practical terms: every book in the 10,000-title catalog is scored against your stated preferences in a single pass, filtered down to only the books that meet your hard requirements, and then the ten highest-scoring titles are returned to you.

The underlying model achieves a **ROC-AUC of 0.858** and **77.1% accuracy** on held-out test data, meaning its predictions of what a reader will like are well above chance and grounded in real reading behavior rather than simple popularity.

---

## Using the Web Interface

The application homepage presents a single preference form. To get recommendations:

1. **Select your Genres** — choose one or more genres from the tile selector (e.g., Fantasy, Thriller, Romance).
2. **Select your Mood** — choose the mood or tone you're looking for (e.g., Cozy, Escapist, Dark).
3. **Set your Minimum Rating** — drag the rating slider to the lowest average Goodreads rating you're willing to accept.
4. **Set your Maximum Runtime** — drag the length slider to your preferred maximum book length, expressed in estimated reading hours.
5. **Choose an Era** — select Recent, Classic, or Any.
6. **Choose a Popularity level** — select Popular or Underrated.
7. **Submit the form** — your top 10 personalized recommendations will appear below, each shown as a book card.

---

## Understanding the Filters

| Filter | What It Does |
|---|---|
| **Genres** | Shapes the recommendation toward books matching your selected genre(s). This is a *soft* preference — it influences ranking rather than strictly excluding books. |
| **Mood** | Steers results toward books with a matching tone (e.g., Cozy, Dark, Escapist), based on language used in each book's description. |
| **Popularity** | *Popular* applies no restriction. *Underrated* excludes any book with more than 65,000 ratings (roughly the most-rated 15% of the catalog), surfacing lesser-known titles. |
| **Minimum Rating** | A **hard filter** — any book with an average rating below your selected threshold is excluded entirely, regardless of how well it otherwise matches your preferences. |
| **Maximum Runtime** | A **hard filter** on page count, converted at a rate of 50 pages per estimated reading hour (for example, a 30-hour limit excludes any book longer than 1,500 pages). |
| **Era** | *Recent* limits results to books published in the year 2000 or later. *Classic* limits results to books published before 1980. *Any* applies no restriction. |

---

## Reading Your Recommendations

Each recommended title is displayed as a **Book Card**, containing:

- Cover image
- Title and author
- A short pitch/description of the book
- Genre chips
- Average rating and total ratings count
- Page count
- Publication year
- A **Match score**, indicating how strongly the book aligns with your stated preferences (higher is a stronger match)

Recommendations are always sorted from strongest to weakest match, with the highest-scoring book listed first.

---

## Default Preferences

If you submit the form without changing anything, GOOD/BOOKS uses the following defaults:

| Filter | Default Value |
|---|---|
| Genres | Fantasy, Sci-Fi, Thriller |
| Mood | Cozy |
| Popularity | Popular |
| Minimum Rating | ★ 4.0 |
| Maximum Runtime | 30 hours (≈1,500 pages) |
| Era | Recent (2000 or later) |

---

## API Reference (For Developers)

Developers integrating with or extending GOOD/BOOKS can call the backend API directly.

**Base URL (local installation):** `http://localhost:18000`
**Interactive documentation (Swagger):** `http://localhost:18000/docs`

### `POST /api/recommend`

Returns up to 10 personalized book recommendations.

**Request body:**
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

**Response body:**
```json
{
  "books": [
    {
      "title":          "The Name of the Wind",
      "author":         "Patrick Rothfuss",
      "genres":         ["Fantasy", "Fiction"],
      "moods":          [],
      "pitch":          "A legendary figure recounts his life story...",
      "match":          92,
      "average_rating": 4.55,
      "ratings_count":  497765,
      "pages":          662,
      "image_url":      "https://...",
      "pub_year":       2007
    }
  ],
  "count": 10,
  "query": { }
}
```

### Other Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Returns backend health status and confirms whether the database has been seeded. |
| `GET /api/options/genres` | Returns the list of available genre labels, sourced from the loaded ML model. |
| `GET /api/options/moods` | Returns the list of available mood labels, sourced from the loaded ML model. |

---

## System Architecture Overview

GOOD/BOOKS is composed of two main services that communicate over an internal network:

- **Frontend** — A React 18 + TypeScript application (built with Vite) that presents the preference form and displays results.
- **Backend** — A Python 3.11 FastAPI service that hosts the trained MLP model and serves recommendations, backed by a SQLite database containing the full Goodbooks-10K catalog.

Both services run as Docker containers connected via an internal bridge network, with the book database persisted through a Docker volume so that data survives container restarts.

---

## Dataset Information

GOOD/BOOKS is built on the **Goodbooks-10K** dataset (Zygmunt Zając, available on Kaggle), which includes:

- 10,000 of the most popular books on Goodreads
- 981,756 individual user ratings from 53,424 users
- Tag and genre metadata sourced from Goodreads bookshelves

This dataset underpins both the recommendation model's training data and the searchable catalog shown in the app.

---

## Frequently Asked Questions

**Q: Do I need to create an account to get recommendations?**
No. Simply set your preferences and submit the form — no login is required.

**Q: Why did I get fewer than 10 recommendations?**
This happens when your hard filters (minimum rating, maximum runtime, era, or popularity) are strict enough that fewer than 10 books in the 10,000-title catalog qualify. Try relaxing one of these filters.

**Q: What does "Underrated" mean under Popularity?**
It excludes the most-rated 15% of books (over 65,000 ratings), surfacing well-matched titles that haven't already been mass-recommended everywhere else.

**Q: How is "Match" calculated?**
It reflects the probability, as estimated by the trained MLP model, that a reader with your stated preferences will enjoy that specific book — expressed as a percentage.

**Q: Can I run GOOD/BOOKS on my own machine?**
Yes. See the accompanying *Installation Guide* for full setup instructions using Docker or a manual local setup.

---

*GOOD/BOOKS — User Manual — Page generated for internal and end-user distribution.*
