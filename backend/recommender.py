"""
recommender.py — Core recommendation engine for SHELF/MATCH.

Algorithm
---------
1.  Map user-selected genres/moods → Goodreads tag names via lookup tables.
2.  Resolve tag names → tag_ids (batch SQL lookup in tags table).
3.  Run an aggregated SQL query:
        · LEFT JOIN genre tag counts  (SUM of matching tag counts per book)
        · LEFT JOIN mood  tag counts
        · Filter by average_rating ≥ 3.5 and optional page cap
4.  Score each candidate book with a weighted formula (normalised 0–1):
        genre_score * 0.50  +  mood_score * 0.25
        + quality * 0.17    +  popularity * 0.08
5.  Convert to match percentage (min 50 so no book looks terrible).
6.  Detect which of the user's selected moods actually matched each book
    (for display as tag chips on the card).
7.  Parse the `genres` JSON column and map to display labels.
8.  Return top-12 deduplicated results.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from typing import List, Optional

from models import BookResult, RecommendRequest

log = logging.getLogger(__name__)

# ── Genre → Goodreads tag name list ────────────────────────────────────────────
GENRE_TAG_MAP: dict[str, list[str]] = {
    "Fantasy":          ["fantasy", "high-fantasy", "epic-fantasy", "fantasy-fiction",
                         "urban-fantasy", "dark-fantasy", "sword-and-sorcery"],
    "Sci-Fi":           ["science-fiction", "sci-fi", "scifi", "space-opera",
                         "hard-science-fiction", "dystopia", "cyberpunk"],
    "Mystery":          ["mystery", "cozy-mystery", "detective", "whodunit",
                         "mystery-thriller", "british-mysteries"],
    "Romance":          ["romance", "contemporary-romance", "historical-romance",
                         "romantic", "love-story", "romance-novels"],
    "Literary Fiction": ["literary-fiction", "literary", "contemporary-fiction",
                         "classics", "general-fiction", "contemporary", "fiction"],
    "Horror":           ["horror", "horror-fiction", "supernatural", "gothic",
                         "paranormal-horror", "ghost-stories"],
    "Non-Fiction":      ["non-fiction", "nonfiction", "self-help", "biography",
                         "memoir", "history", "true-crime", "popular-science"],
    "Thriller":         ["thriller", "suspense", "psychological-thriller",
                         "crime-thriller", "crime", "political-thriller"],
    "Historical":       ["historical-fiction", "historical", "historical-romance",
                         "historical-mystery", "medieval"],
}

# ── Mood → Goodreads tag name list ─────────────────────────────────────────────
MOOD_TAG_MAP: dict[str, list[str]] = {
    "Cozy":              ["cozy", "cozy-mystery", "feel-good", "comfort-reads",
                          "light-read", "wholesome", "warm"],
    "Dark & Twisty":     ["dark", "dark-fiction", "noir", "gritty",
                          "dark-romance", "dark-humor", "bleak"],
    "Fast-Paced":        ["fast-paced", "action", "page-turner", "action-adventure",
                          "adventure", "gripping", "plot-driven"],
    "Slow Burn":         ["slow-burn", "character-driven", "literary", "quiet",
                          "introspective", "slow-paced"],
    "Thought-Provoking": ["thought-provoking", "philosophical", "classics",
                          "literary-fiction", "intellectual", "profound"],
    "Escapist":          ["fantasy", "adventure", "magic", "world-building",
                          "epic", "escapism", "quest"],
    "Heartwarming":      ["heartwarming", "feel-good", "uplifting", "sweet",
                          "touching", "inspiring", "feel-good-fiction"],
    "Unsettling":        ["horror", "dark", "psychological", "disturbing",
                          "creepy", "eerie", "unsettling", "disturbing-fiction"],
}

# ── Genre display name map ──────────────────────────────────────────────────────
_GENRE_DISPLAY: dict[str, str] = {
    "fantasy": "Fantasy",       "science-fiction": "Sci-Fi",  "sci-fi": "Sci-Fi",
    "mystery": "Mystery",       "romance": "Romance",          "literary-fiction": "Literary",
    "literary": "Literary",     "horror": "Horror",            "non-fiction": "Non-Fiction",
    "nonfiction": "Non-Fiction","thriller": "Thriller",        "suspense": "Thriller",
    "historical-fiction": "Historical", "historical": "Historical",
    "young-adult": "YA",        "contemporary": "Contemporary","classics": "Classics",
    "biography": "Biography",   "memoir": "Memoir",            "self-help": "Self-Help",
    "crime": "Crime",           "dystopia": "Dystopian",       "paranormal": "Paranormal",
    "fiction": "Fiction",       "general-fiction": "Fiction",
}

# Empirical normalisation constants (based on goodbooks-10k tag count distribution)
_MAX_GENRE_SCORE = 800_000
_MAX_MOOD_SCORE  = 200_000


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_tag_ids(conn: sqlite3.Connection, tag_names: list[str]) -> list[int]:
    """Return tag_ids for a list of tag names (exact match only)."""
    if not tag_names:
        return []
    placeholders = ",".join("?" * len(tag_names))
    rows = conn.execute(
        f"SELECT tag_id FROM tags WHERE tag_name IN ({placeholders})",
        tag_names
    ).fetchall()
    return [r["tag_id"] for r in rows]


def _parse_genres(genres_json: Optional[str]) -> list[str]:
    """Decode the JSON genre array stored in the books table."""
    if not genres_json:
        return []
    try:
        return json.loads(genres_json)
    except Exception:
        return []


def _map_display_genres(raw: list[str]) -> list[str]:
    """Convert raw tag-style genre strings to display labels, deduplicated."""
    seen: set[str] = set()
    result: list[str] = []
    for g in raw:
        label = _GENRE_DISPLAY.get(g.lower(), g.capitalize())
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result[:4]


def _infer_formats(ratings_count: int) -> list[str]:
    """Heuristic: very popular books tend to have audiobooks too."""
    fmts = ["Physical", "E-book"]
    if ratings_count > 50_000:
        fmts.append("Audiobook")
    return fmts


def _compute_match(
    genre_score: float,
    mood_score: float,
    average_rating: float,
    ratings_count: int,
) -> int:
    g_norm = min(genre_score / _MAX_GENRE_SCORE, 1.0)
    m_norm = min(mood_score  / _MAX_MOOD_SCORE,  1.0)
    q_norm = max(0.0, (average_rating - 2.0) / 3.0)  # 2–5 → 0–1
    p_norm = min(math.log10(max(ratings_count, 1)) / 6.0, 1.0)

    weighted = g_norm * 0.50 + m_norm * 0.25 + q_norm * 0.17 + p_norm * 0.08
    return max(50, round(weighted * 100))


def _get_book_mood_matches(
    conn: sqlite3.Connection,
    book_ids: list[int],
    moods: list[str],
) -> dict[int, list[str]]:
    """For each book_id, return which of the user's moods it actually has tags for."""
    result: dict[int, list[str]] = {}
    if not book_ids or not moods:
        return result

    id_list = ",".join(str(b) for b in book_ids)
    for mood in moods:
        tag_ids = _resolve_tag_ids(conn, MOOD_TAG_MAP.get(mood, []))
        if not tag_ids:
            continue
        tid_list = ",".join(str(t) for t in tag_ids)
        rows = conn.execute(
            f"SELECT DISTINCT book_id FROM book_tags "
            f"WHERE book_id IN ({id_list}) AND tag_id IN ({tid_list}) AND count > 30"
        ).fetchall()
        for row in rows:
            result.setdefault(row["book_id"], []).append(mood)

    return result


# ── Main recommendation function ───────────────────────────────────────────────

def get_recommendations(conn: sqlite3.Connection, req: RecommendRequest) -> list[BookResult]:
    """
    Return up to 12 ranked BookResult objects for the given RecommendRequest.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open database connection.
    req  : RecommendRequest
        Parsed frontend form payload.
    """
    genre_tag_names = [t for g in req.genres for t in GENRE_TAG_MAP.get(g, [])]
    mood_tag_names  = [t for m in req.moods  for t in MOOD_TAG_MAP.get(m, [])]

    genre_tag_ids = _resolve_tag_ids(conn, genre_tag_names)
    mood_tag_ids  = _resolve_tag_ids(conn, mood_tag_names)

    no_genres = len(genre_tag_ids) == 0
    no_moods  = len(mood_tag_ids)  == 0

    # Build optional tag-score subqueries
    def tag_join(ids: list[int], alias: str) -> str:
        if not ids:
            return ""
        id_str = ",".join(str(i) for i in ids)
        return f"""
        LEFT JOIN (
            SELECT book_id, SUM(count) AS {alias}
            FROM book_tags
            WHERE tag_id IN ({id_str})
            GROUP BY book_id
        ) {alias}_q ON {alias}_q.book_id = b.id"""

    genre_join = tag_join(genre_tag_ids, "genre_score")
    mood_join  = tag_join(mood_tag_ids,  "mood_score")

    page_where  = "" if req.maxPages >= 900 else "AND (b.pages IS NULL OR b.pages <= :max_pages)"
    genre_where = "" if no_genres           else "AND COALESCE(genre_score_q.genre_score, 0) > 0"

    sql = f"""
        SELECT
            b.id,
            b.title,
            b.authors,
            b.average_rating,
            b.ratings_count,
            b.pub_year,
            b.pages,
            b.description,
            b.genres,
            b.image_url,
            COALESCE(genre_score_q.genre_score, 0) AS genre_score,
            COALESCE(mood_score_q.mood_score,  0) AS mood_score
        FROM books b
        {genre_join}
        {mood_join}
        WHERE b.average_rating >= 3.5
          {page_where}
          {genre_where}
        ORDER BY
            (
                COALESCE(genre_score_q.genre_score, 0) * 0.5 +
                COALESCE(mood_score_q.mood_score,  0) * 0.3 +
                b.average_rating * 20000 +
                MIN(b.ratings_count, 500000) * 0.01
            ) DESC
        LIMIT 30
    """

    rows = conn.execute(sql, {"max_pages": req.maxPages}).fetchall()

    if not rows:
        log.info("No results found; falling back to top-rated books")
        return _fallback_top(conn, 12)

    # Detect which moods matched per book
    book_ids   = [r["id"] for r in rows]
    mood_map   = _get_book_mood_matches(conn, book_ids, req.moods)

    results: list[BookResult] = []
    seen_titles: set[str] = set()

    for r in rows:
        title = r["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)

        raw_genres   = _parse_genres(r["genres"])
        disp_genres  = _map_display_genres(raw_genres)
        matched_moods = mood_map.get(r["id"], [])
        match_pct    = _compute_match(r["genre_score"], r["mood_score"],
                                      r["average_rating"], r["ratings_count"])

        results.append(BookResult(
            title          = title,
            author         = r["authors"] or "Unknown",
            genres         = disp_genres,
            moods          = matched_moods,
            pages          = r["pages"],
            formats        = _infer_formats(r["ratings_count"]),
            pitch          = r["description"] or "",
            match          = match_pct,
            average_rating = r["average_rating"],
            ratings_count  = r["ratings_count"],
            image_url      = r["image_url"] or "",
            pub_year       = r["pub_year"],
        ))

    results.sort(key=lambda b: b.match, reverse=True)
    return results[:12]


def _fallback_top(conn: sqlite3.Connection, limit: int = 12) -> list[BookResult]:
    """Return the most-reviewed highly-rated books when no filters match."""
    rows = conn.execute(
        "SELECT * FROM books WHERE average_rating >= 4.0 ORDER BY ratings_count DESC LIMIT ?",
        (limit,)
    ).fetchall()
    results = []
    for r in rows:
        raw_genres = _parse_genres(r["genres"])
        results.append(BookResult(
            title          = r["title"],
            author         = r["authors"] or "Unknown",
            genres         = _map_display_genres(raw_genres),
            moods          = [],
            pages          = r["pages"],
            formats        = _infer_formats(r["ratings_count"]),
            pitch          = r["description"] or "",
            match          = max(50, round(70 + (r["average_rating"] - 4.0) * 15)),
            average_rating = r["average_rating"],
            ratings_count  = r["ratings_count"],
            image_url      = r["image_url"] or "",
            pub_year       = r["pub_year"],
        ))
    return results
