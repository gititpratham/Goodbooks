"""
recommender.py — Core recommendation engine for SHELF/MATCH.

Algorithm
---------
1.  Map user-selected genres/moods → Goodreads tag names via lookup tables.
2.  Resolve tag names → tag_ids (SQL lookup in tags table).
3.  Aggregate tag counts per book via LEFT JOIN subqueries:
        genre_score = SUM of matching genre tag counts
        mood_score  = SUM of matching mood  tag counts
4.  Apply hard filters: min_rating, pub_era.
5.  Score each candidate with a weighted formula:
        genre_score  * 0.55   (normalised 0-1)
        mood_score   * 0.25
        rating_qual  * 0.15   (normalised, 3.5-5 → 0-1)
        popularity   * 0.05   (log10 scale)
6.  Convert to match percentage (scale so top result ≈ 95-100%).
7.  Return only books whose match ≥ 90% OR the top-3 if fewer qualify.
"""

from __future__ import annotations

import logging
import math
import sqlite3

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
    "Young Adult":      ["young-adult", "ya", "ya-fiction", "teen",
                         "young-adult-fiction", "ya-fantasy"],
    "Graphic Novel":    ["graphic-novel", "comics", "manga", "graphic-novels",
                         "comic-book", "sequential-art"],
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
                          "creepy", "eerie", "unsettling"],
}

# ── Genre display labels for matched tag names ──────────────────────────────────
_GENRE_DISPLAY: dict[str, str] = {
    "fantasy": "Fantasy",           "science-fiction": "Sci-Fi",    "sci-fi": "Sci-Fi",
    "mystery": "Mystery",           "romance": "Romance",            "literary-fiction": "Literary",
    "literary": "Literary",         "horror": "Horror",              "non-fiction": "Non-Fiction",
    "nonfiction": "Non-Fiction",    "thriller": "Thriller",          "suspense": "Thriller",
    "historical-fiction": "Historical", "historical": "Historical",
    "young-adult": "YA",            "contemporary": "Contemporary",  "classics": "Classics",
    "biography": "Biography",       "memoir": "Memoir",              "self-help": "Self-Help",
    "crime": "Crime",               "dystopia": "Dystopian",         "paranormal": "Paranormal",
    "fiction": "Fiction",           "general-fiction": "Fiction",    "graphic-novel": "Graphic Novel",
}

# Empirical constants — max observed genre/mood cumulative tag counts in goodbooks-10k
# Tightened so that mid-tier tag matches (not just Harry Potter) score above 0.3+
_MAX_GENRE_SCORE = 300_000.0
_MAX_MOOD_SCORE  = 80_000.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_tag_ids(conn: sqlite3.Connection, tag_names: list[str]) -> list[int]:
    """Return tag_ids for a list of tag names (exact match)."""
    if not tag_names:
        return []
    placeholders = ",".join("?" * len(tag_names))
    rows = conn.execute(
        f"SELECT tag_id FROM tags WHERE tag_name IN ({placeholders})",
        tag_names
    ).fetchall()
    return [r["tag_id"] for r in rows]


def _get_matched_genre_names(
    conn: sqlite3.Connection,
    book_ids: list[int],
    genres: list[str],
) -> dict[int, list[str]]:
    """Return display genre labels for books that actually carry those genre tags."""
    result: dict[int, list[str]] = {}
    if not book_ids or not genres:
        return result

    id_list = ",".join(str(b) for b in book_ids)
    for genre in genres:
        tag_names = GENRE_TAG_MAP.get(genre, [])
        tag_ids   = _resolve_tag_ids(conn, tag_names)
        if not tag_ids:
            continue
        tid_list = ",".join(str(t) for t in tag_ids)
        rows = conn.execute(
            f"SELECT DISTINCT book_id FROM book_tags "
            f"WHERE book_id IN ({id_list}) AND tag_id IN ({tid_list}) AND count > 20"
        ).fetchall()
        label = _GENRE_DISPLAY.get(tag_names[0].lower(), genre)
        for row in rows:
            result.setdefault(row["book_id"], []).append(label)

    # Deduplicate labels per book
    return {bid: list(dict.fromkeys(labels))[:4] for bid, labels in result.items()}


def _get_matched_moods(
    conn: sqlite3.Connection,
    book_ids: list[int],
    moods: list[str],
) -> dict[int, list[str]]:
    """Return which user-selected moods actually match each book via tags."""
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


def _compute_raw_score(
    genre_score: float,
    mood_score: float,
    average_rating: float,
    ratings_count: int,
) -> float:
    """Produce a raw 0-1 weighted score for a book.

    genre_score is the per-genre AVERAGE (SQL does the averaging).
    A book matching all 3 selected genres scores near 1.0; a book
    matching only 1 of 3 genres scores ~0.33, creating genuine sensitivity.

    Weights:
        Genre avg strength  60%
        Mood  tag strength  25%
        Rating quality      10%
        Popularity           5%
    """
    g_norm = min(genre_score / _MAX_GENRE_SCORE, 1.0)
    m_norm = min(mood_score  / _MAX_MOOD_SCORE,  1.0)
    # Quality: normalise 3.5-5 → 0-1
    q_norm = max(0.0, (average_rating - 3.5) / 1.5)
    # Popularity: log10(count) / 6 — modest influence
    p_norm = min(math.log10(max(ratings_count, 1)) / 6.0, 1.0)

    return g_norm * 0.60 + m_norm * 0.25 + q_norm * 0.10 + p_norm * 0.05


def _to_match_pct(raw: float) -> int:
    """Convert a raw 0-1 score to a match percentage on an absolute scale.

    Uses a fixed mapping (not relative to the batch max) so that removing a
    genre genuinely lowers the match % for books that no longer fully qualify.
    Scale: raw 0.6 → 90%, raw 0.8 → 100%.  Below 0.3 → 45% floor.
    """
    # Linear stretch: 0.3–0.8 maps to 45%–100%
    pct = 45.0 + (raw - 0.3) / 0.5 * 55.0
    return max(1, min(100, round(pct)))


# ── Main recommendation function ───────────────────────────────────────────────

def get_recommendations(conn: sqlite3.Connection, req: RecommendRequest) -> list[BookResult]:
    """
    Return the top-3 books, or all books with match ≥ 90%, whichever is more.

    Scoring approach (sensitivity-aware):
        - Build one subquery per selected genre so books are scored on
          how well they match EACH genre, not just any genre in the pool.
        - genre_score = average of per-genre scores × genre_coverage_bonus
          where coverage = fraction of selected genres the book actually has.
        - This means removing "Graphic Novel" genuinely changes which
          books bubble to the top.
    """
    mood_tag_names  = [t for m in req.moods  for t in MOOD_TAG_MAP.get(m, [])]
    mood_tag_ids    = _resolve_tag_ids(conn, mood_tag_names)
    no_moods        = len(mood_tag_ids) == 0

    # ── Per-genre subqueries ──────────────────────────────────────────────────
    per_genre_joins:   list[str]   = []
    per_genre_selects: list[str]   = []   # column expressions for SELECT

    for i, genre in enumerate(req.genres):
        tag_names = GENRE_TAG_MAP.get(genre, [])
        tag_ids   = _resolve_tag_ids(conn, tag_names)
        if not tag_ids:
            continue
        alias   = f"g{i}"
        id_str  = ",".join(str(t) for t in tag_ids)
        per_genre_joins.append(f"""
        LEFT JOIN (
            SELECT book_id, SUM(count) AS score
            FROM book_tags
            WHERE tag_id IN ({id_str})
            GROUP BY book_id
        ) {alias} ON {alias}.book_id = b.id""")
        per_genre_selects.append(f"COALESCE({alias}.score, 0)")

    # Combined genre score = average of per-genre scores (normalised by _MAX_GENRE_SCORE)
    n_genre_aliases = len(per_genre_selects)
    if n_genre_aliases > 0:
        genre_avg_expr = "(" + " + ".join(per_genre_selects) + f") / {n_genre_aliases}.0"
    else:
        genre_avg_expr = "0"

    no_genres = n_genre_aliases == 0

    # ── Mood subquery ─────────────────────────────────────────────────────────
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
        ) {alias}_tbl ON {alias}_tbl.book_id = b.id"""

    mood_join    = tag_join(mood_tag_ids, "mood_score")
    mood_select  = "COALESCE(mood_score_tbl.mood_score, 0)" if not no_moods else "0"

    # ── Hard filters ──────────────────────────────────────────────────────────
    # Require that at least ONE genre subquery has a hit (sum > 0)
    genre_where  = f"AND ({genre_avg_expr}) > 0" if not no_genres else ""
    rating_where = f"AND b.average_rating >= {req.minRating}"
    pub_where    = ""
    if req.pubEra == "recent":
        pub_where = "AND b.pub_year IS NOT NULL AND b.pub_year >= 2000"
    elif req.pubEra == "classic":
        pub_where = "AND b.pub_year IS NOT NULL AND b.pub_year < 1980"

    # Build ORDER BY using the same genre_avg_expr
    order_genre = f"({genre_avg_expr} / {_MAX_GENRE_SCORE}) * 0.60" if not no_genres else "0"
    order_mood  = f"({mood_select} / {_MAX_MOOD_SCORE}) * 0.25" if not no_moods else "0"

    genre_joins_sql = "\n".join(per_genre_joins)

    sql = f"""
        SELECT
            b.id,
            b.title,
            b.authors,
            b.average_rating,
            b.ratings_count,
            b.pub_year,
            b.image_url,
            b.description,
            ({genre_avg_expr}) AS genre_score,
            {mood_select}      AS mood_score
        FROM books b
        {genre_joins_sql}
        {mood_join}
        WHERE 1=1
          {rating_where}
          {pub_where}
          {genre_where}
        ORDER BY
            (
                {order_genre} +
                {order_mood}  +
                ((b.average_rating - 3.5) / 1.5) * 0.10 +
                (MIN(CAST(b.ratings_count AS REAL), 1000000.0) / 1000000.0) * 0.05
            ) DESC
        LIMIT 50
    """

    rows = conn.execute(sql).fetchall()

    if not rows:
        log.info("No results found for query; returning fallback top-rated books")
        return _fallback_top(conn, req.minRating, 3)

    # Compute raw scores and find the maximum for normalisation
    scored = []
    for r in rows:
        raw = _compute_raw_score(
            r["genre_score"], r["mood_score"],
            r["average_rating"], r["ratings_count"],
        )
        scored.append((r, raw))

    max_raw = max(s for _, s in scored)  # kept for logging / future use

    # Build match percentages using absolute scale
    with_match = [(r, _to_match_pct(raw)) for r, raw in scored]

    # Collect book ids for bulk mood/genre lookups
    book_ids = [r["id"] for r, _ in with_match]
    mood_map  = _get_matched_moods(conn, book_ids, req.moods)
    genre_map = _get_matched_genre_names(conn, book_ids, req.genres)

    results: list[BookResult] = []
    seen: set[str] = set()

    for r, match_pct in with_match:
        title = (r["title"] or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)

        results.append(BookResult(
            title          = title,
            author         = (r["authors"] or "Unknown").strip(),
            genres         = genre_map.get(r["id"], []),
            moods          = mood_map.get(r["id"], []),
            pitch          = r["description"] or "",
            match          = match_pct,
            average_rating = r["average_rating"],
            ratings_count  = r["ratings_count"],
            image_url      = r["image_url"] or "",
            pub_year       = r["pub_year"],
        ))

    # Filter: keep ≥70% match books, but guarantee at least top-5
    high_match = [b for b in results if b.match >= 70]
    final = high_match if len(high_match) >= 5 else results[:5]

    return final


def _fallback_top(
    conn: sqlite3.Connection,
    min_rating: float = 3.5,
    limit: int = 3,
) -> list[BookResult]:
    """Return the best-rated most-reviewed books as a fallback."""
    rows = conn.execute(
        """SELECT * FROM books
           WHERE average_rating >= ?
           ORDER BY ratings_count DESC
           LIMIT ?""",
        (min_rating, limit * 4)
    ).fetchall()

    results = []
    seen: set[str] = set()
    for r in rows:
        title = (r["title"] or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        results.append(BookResult(
            title          = title,
            author         = (r["authors"] or "Unknown").strip(),
            genres         = [],
            moods          = [],
            pitch          = r["description"] or "",
            match          = max(50, round(60 + (r["average_rating"] - min_rating) * 20)),
            average_rating = r["average_rating"],
            ratings_count  = r["ratings_count"],
            image_url      = r["image_url"] or "",
            pub_year       = r["pub_year"],
        ))
        if len(results) >= limit:
            break

    return results
