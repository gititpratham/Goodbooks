/**
 * db.ts — SQLite connection singleton + schema creation
 *
 * Uses better-sqlite3 (synchronous, zero-config, fast).
 * The database file lives at api/goodbooks.db (auto-created on first run).
 */

import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'goodbooks.db');

const db = new Database(DB_PATH);

// Performance tuning
db.pragma('journal_mode = WAL');
db.pragma('synchronous = NORMAL');
db.pragma('foreign_keys = ON');
db.pragma('cache_size = -64000'); // 64 MB cache

// ─── Schema ─────────────────────────────────────────────────────────
export function createSchema(): void {
  db.exec(`
    -- ── Books (primary metadata from books_enriched.csv) ──────────
    CREATE TABLE IF NOT EXISTS books (
      id              INTEGER PRIMARY KEY,   -- sequential 1-10000
      title           TEXT    NOT NULL,
      authors         TEXT,                  -- first listed author
      all_authors     TEXT,                  -- full list, JSON array
      average_rating  REAL    DEFAULT 0,
      ratings_count   INTEGER DEFAULT 0,
      pub_year        INTEGER,
      pages           INTEGER,
      description     TEXT,
      genres          TEXT,                  -- JSON array of strings
      image_url       TEXT,
      language_code   TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_books_rating  ON books (average_rating DESC);
    CREATE INDEX IF NOT EXISTS idx_books_count   ON books (ratings_count  DESC);
    CREATE INDEX IF NOT EXISTS idx_books_pages   ON books (pages);
    CREATE INDEX IF NOT EXISTS idx_books_year    ON books (pub_year);

    -- ── Tags (from tags.csv) ────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS tags (
      tag_id   INTEGER PRIMARY KEY,
      tag_name TEXT    NOT NULL UNIQUE
    );

    CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (tag_name);

    -- ── Book-Tag associations (from book_tags.csv) ──────────────────
    -- book_tags.goodreads_book_id = books.id (sequential, NOT goodreads ID)
    CREATE TABLE IF NOT EXISTS book_tags (
      book_id  INTEGER NOT NULL,
      tag_id   INTEGER NOT NULL,
      count    INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (book_id, tag_id),
      FOREIGN KEY (book_id) REFERENCES books (id),
      FOREIGN KEY (tag_id)  REFERENCES tags  (tag_id)
    );

    CREATE INDEX IF NOT EXISTS idx_bt_tag  ON book_tags (tag_id,  count DESC);
    CREATE INDEX IF NOT EXISTS idx_bt_book ON book_tags (book_id, count DESC);
  `);
}

// Register custom math functions SQLite lacks
db.function('LN', (x: number) => (x > 0 ? Math.log(x) : 0));
db.function('LOG10', (x: number) => (x > 0 ? Math.log10(x) : 0));

export default db;
