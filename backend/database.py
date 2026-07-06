"""
database.py — SQLite connection, schema creation, and CSV seeding.

Data sources (from Goodbooks-10k Kaggle dataset)
-------------------------------------------------
books.csv     →  books table   (title, authors, ratings — id = sequential row number 1..10000)
tags.csv      →  tags  table   (tag_id, tag_name)
book_tags.csv →  book_tags     (goodreads_book_id = sequential row id, tag_id, count)

Key join: book_tags.goodreads_book_id == books.id  (sequential row number, NOT books.book_id)

Path resolution
---------------
Set these env vars to override defaults (used by Docker):
    DB_PATH       path to SQLite file
    BOOKS_CSV     path to books.csv
    TAGS_CSV      path to tags.csv
    BOOK_TAGS_CSV path to book_tags.csv
"""

from __future__ import annotations

import csv
import logging
import os
import sqlite3
import time
from pathlib import Path

log = logging.getLogger(__name__)

# ── Path resolution ────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent

DB_PATH       = Path(os.environ.get("DB_PATH",       str(_HERE / "goodbooks.db")))
BOOKS_CSV     = Path(os.environ.get("BOOKS_CSV",     str(_HERE / "db" / "books_with_descriptions.csv")))
TAGS_CSV      = Path(os.environ.get("TAGS_CSV",      str(_HERE / "db" / "tags.csv")))
BOOK_TAGS_CSV = Path(os.environ.get("BOOK_TAGS_CSV", str(_HERE / "db" / "book_tags.csv")))

# ── Connection factory ─────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a new WAL-mode SQLite connection with row_factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-32000")  # 32 MB page cache
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY,   -- sequential row id (1..10000), matches book_tags.goodreads_book_id
    goodreads_id    INTEGER,               -- the actual Goodreads book_id
    title           TEXT    NOT NULL,
    authors         TEXT,
    average_rating  REAL    DEFAULT 0,
    ratings_count   INTEGER DEFAULT 0,
    pub_year        INTEGER,
    image_url       TEXT,
    language_code   TEXT,
    description     TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_rating ON books (average_rating DESC);
CREATE INDEX IF NOT EXISTS idx_books_count  ON books (ratings_count  DESC);

CREATE TABLE IF NOT EXISTS tags (
    tag_id   INTEGER PRIMARY KEY,
    tag_name TEXT    NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (tag_name);

CREATE TABLE IF NOT EXISTS book_tags (
    book_id  INTEGER NOT NULL,
    tag_id   INTEGER NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (book_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_bt_tag  ON book_tags (tag_id,  count DESC);
CREATE INDEX IF NOT EXISTS idx_bt_book ON book_tags (book_id, count DESC);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


# ── Seeder ────────────────────────────────────────────────────────────────────

def is_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()
    return (row["c"] if row else 0) > 0


def seed(conn: sqlite3.Connection) -> None:
    """Populate books, tags, and book_tags from CSV files (runs once)."""

    log.info("═" * 56)
    log.info("  GOODBOOKS — Seeding SQLite database")
    log.info("═" * 56)

    # ── 1. books ──────────────────────────────────────────────────────────────
    # CRITICAL: Use the sequential 'id' column as PRIMARY KEY so it matches
    # book_tags.goodreads_book_id (which is 1..10000, not the Goodreads book_id).
    log.info("[1/3] Seeding books from %s …", BOOKS_CSV)
    if not BOOKS_CSV.exists():
        raise FileNotFoundError(f"books.csv not found at {BOOKS_CSV}")

    insert_book = """
        INSERT OR REPLACE INTO books
            (id, goodreads_id, title, authors, average_rating,
             ratings_count, pub_year, image_url, language_code, description)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """
    books_rows: list[tuple] = []
    with open(BOOKS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 'id' is the sequential row number (1..10000) — this MUST match book_tags.goodreads_book_id
            seq_id = int(r["id"])
            # 'book_id' is the actual Goodreads identifier
            goodreads_id = int(r["book_id"])

            # Authors: raw CSV is comma-separated, take the first
            authors_raw = r.get("authors", "").split(",")
            first_author = authors_raw[0].strip() if authors_raw else "Unknown"

            # Publication year: stored as float e.g. "1997.0"
            pub_year = None
            py_raw = r.get("original_publication_year", "").strip()
            if py_raw and py_raw.lower() not in ("", "nan"):
                try:
                    pub_year = int(float(py_raw))
                except (ValueError, OverflowError):
                    pass

            books_rows.append((
                seq_id,
                goodreads_id,
                (r.get("original_title") or r.get("title") or "").strip(),
                first_author,
                float(r.get("average_rating") or 0),
                int(r.get("ratings_count") or 0),
                pub_year,
                r.get("image_url", "").strip(),
                r.get("language_code", "eng").strip(),
                r.get("description", "").strip(),
            ))

    with conn:
        conn.executemany(insert_book, books_rows)
    log.info("  → Inserted %d books ✓", len(books_rows))

    # ── 2. tags ───────────────────────────────────────────────────────────────
    log.info("[2/3] Seeding tags from %s …", TAGS_CSV)
    if not TAGS_CSV.exists():
        raise FileNotFoundError(f"tags.csv not found at {TAGS_CSV}")

    tag_rows: list[tuple] = []
    with open(TAGS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            tag_rows.append((int(r["tag_id"]), r["tag_name"]))

    with conn:
        conn.executemany("INSERT OR IGNORE INTO tags (tag_id, tag_name) VALUES (?,?)", tag_rows)
    log.info("  → Inserted %d tags ✓", len(tag_rows))

    # ── 3. book_tags (streamed in 10k-row batches for efficiency) ─────────────
    log.info("[3/3] Seeding book_tags from %s (streaming) …", BOOK_TAGS_CSV)
    if not BOOK_TAGS_CSV.exists():
        raise FileNotFoundError(f"book_tags.csv not found at {BOOK_TAGS_CSV}")

    BATCH = 10_000
    batch: list[tuple] = []
    total = 0
    t0 = time.time()

    with open(BOOK_TAGS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # goodreads_book_id here is the sequential id (1..10000) matching books.id
            batch.append((int(r["goodreads_book_id"]), int(r["tag_id"]), int(r["count"])))
            if len(batch) >= BATCH:
                with conn:
                    conn.executemany(
                        "INSERT OR IGNORE INTO book_tags (book_id, tag_id, count) VALUES (?,?,?)",
                        batch
                    )
                total += len(batch)
                batch = []
                if total % 100_000 == 0:
                    log.info("  … %s rows inserted (%.0fs elapsed)", f"{total:,}", time.time() - t0)

    if batch:
        with conn:
            conn.executemany(
                "INSERT OR IGNORE INTO book_tags (book_id, tag_id, count) VALUES (?,?,?)",
                batch
            )
        total += len(batch)

    log.info("  → Inserted %s book_tag rows ✓ (%.1fs)", f"{total:,}", time.time() - t0)
    log.info("═" * 56)
    log.info("  Seeding complete!")
    log.info("═" * 56)
