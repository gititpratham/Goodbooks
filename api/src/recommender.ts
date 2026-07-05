/**
 * recommender.ts — Core recommendation logic
 *
 * Algorithm (hybrid content + tag-based):
 *   1. Map selected genres → genre tag IDs (via tag name lookup)
 *   2. Map selected moods  → mood tag IDs
 *   3. SQL: Fetch candidate books with aggregated tag match scores
 *   4. TypeScript: Compute final weighted score → match %
 *   5. Return formatted top-N results
 */

import db from './db';

// ─── Types ──────────────────────────────────────────────────────────

export interface RecommendRequest {
  genres:   string[];
  moods:    string[];
  maxPages: number;
  format:   string;
}

export interface BookResult {
  title:          string;
  author:         string;
  genres:         string[];
  moods:          string[];
  pages:          number | null;
  formats:        string[];
  pitch:          string;
  match:          number;
  average_rating: number;
  ratings_count:  number;
  image_url:      string;
  pub_year:       number | null;
}

interface RawBook {
  id:             number;
  title:          string;
  authors:        string;        // first author
  average_rating: number;
  ratings_count:  number;
  pub_year:       number | null;
  pages:          number | null;
  description:    string;
  genres:         string;        // JSON string
  image_url:      string;
  genre_score:    number;
  mood_score:     number;
}

// ─── Genre → tag name mappings ──────────────────────────────────────
// Maps each frontend genre label to likely Goodreads shelf tag names
const GENRE_TAG_MAP: Record<string, string[]> = {
  'Fantasy':          ['fantasy', 'high-fantasy', 'epic-fantasy', 'fantasy-fiction', 'urban-fantasy', 'dark-fantasy'],
  'Sci-Fi':           ['science-fiction', 'sci-fi', 'scifi', 'space-opera', 'hard-science-fiction', 'dystopia'],
  'Mystery':          ['mystery', 'cozy-mystery', 'detective', 'whodunit', 'mystery-thriller', 'british-mysteries'],
  'Romance':          ['romance', 'contemporary-romance', 'historical-romance', 'romantic', 'love-story', 'romance-novels'],
  'Literary Fiction': ['literary-fiction', 'literary', 'contemporary-fiction', 'classics', 'general-fiction', 'contemporary'],
  'Horror':           ['horror', 'horror-fiction', 'supernatural', 'gothic', 'paranormal-horror', 'ghost-stories'],
  'Non-Fiction':      ['non-fiction', 'nonfiction', 'self-help', 'biography', 'memoir', 'history', 'true-crime'],
  'Thriller':         ['thriller', 'suspense', 'psychological-thriller', 'crime-thriller', 'crime', 'political-thriller'],
  'Historical':       ['historical-fiction', 'historical', 'historical-romance', 'historical-mystery', 'medieval'],
};

// ─── Mood → tag name mappings ────────────────────────────────────────
const MOOD_TAG_MAP: Record<string, string[]> = {
  'Cozy':              ['cozy', 'cozy-mystery', 'feel-good', 'comfort-reads', 'light-read', 'wholesome'],
  'Dark & Twisty':     ['dark', 'dark-fiction', 'noir', 'gritty', 'dark-romance', 'dark-humor'],
  'Fast-Paced':        ['fast-paced', 'action', 'page-turner', 'action-adventure', 'adventure', 'gripping'],
  'Slow Burn':         ['slow-burn', 'character-driven', 'literary', 'quiet', 'introspective'],
  'Thought-Provoking': ['thought-provoking', 'philosophical', 'classics', 'literary-fiction', 'intellectual'],
  'Escapist':          ['fantasy', 'adventure', 'magic', 'world-building', 'epic', 'escapism'],
  'Heartwarming':      ['heartwarming', 'feel-good', 'uplifting', 'sweet', 'touching', 'inspiring'],
  'Unsettling':        ['horror', 'dark', 'psychological', 'disturbing', 'creepy', 'eerie', 'unsettling'],
};

// Display label mappings (raw tag → nice label shown on cards)
const GENRE_DISPLAY: Record<string, string> = {
  'fantasy': 'Fantasy', 'science-fiction': 'Sci-Fi', 'sci-fi': 'Sci-Fi',
  'mystery': 'Mystery', 'romance': 'Romance', 'literary-fiction': 'Literary',
  'literary': 'Literary', 'horror': 'Horror', 'non-fiction': 'Non-Fiction',
  'nonfiction': 'Non-Fiction', 'thriller': 'Thriller', 'suspense': 'Thriller',
  'historical-fiction': 'Historical', 'historical': 'Historical',
  'young-adult': 'YA', 'contemporary': 'Contemporary', 'classics': 'Classics',
  'biography': 'Biography', 'memoir': 'Memoir', 'self-help': 'Self-Help',
  'crime': 'Crime', 'dystopia': 'Dystopian', 'paranormal': 'Paranormal',
  'graphic-novels': 'Graphic Novel', 'short-stories': 'Short Stories',
  'poetry': 'Poetry', 'chick-lit': 'Chick Lit', 'fiction': 'Fiction',
};

// ─── Utility ─────────────────────────────────────────────────────────

/** Look up tag IDs for a list of tag names (fuzzy: prefix match too) */
function resolveTagIds(tagNames: string[]): number[] {
  if (tagNames.length === 0) return [];
  const placeholders = tagNames.map(() => '?').join(', ');
  const rows = db.prepare(
    `SELECT tag_id FROM tags WHERE tag_name IN (${placeholders})`
  ).all(...tagNames) as { tag_id: number }[];
  return rows.map(r => r.tag_id);
}

/** Parse a JSON array stored in SQLite text column */
function parseJsonArr(raw: string | null): string[] {
  if (!raw) return [];
  try { return JSON.parse(raw) as string[]; }
  catch { return []; }
}

/** Trim description to a readable pitch */
function makePitch(desc: string): string {
  const clean = desc.replace(/\s+/g, ' ').trim();
  if (clean.length <= 220) return clean;
  const truncated = clean.slice(0, 220);
  const lastSpace = truncated.lastIndexOf(' ');
  return (lastSpace > 150 ? truncated.slice(0, lastSpace) : truncated) + '…';
}

/** Infer display formats based on popularity (heuristic, no format data in CSVs) */
function inferFormats(ratingsCount: number): string[] {
  const formats = ['Physical', 'E-book'];
  if (ratingsCount > 50_000) formats.push('Audiobook');
  return formats;
}

/** Map raw genre strings to nice display labels */
function mapGenreLabels(rawGenres: string[]): string[] {
  const labels = rawGenres
    .map(g => GENRE_DISPLAY[g.toLowerCase()] || (g.length > 0 ? g.charAt(0).toUpperCase() + g.slice(1) : ''))
    .filter(Boolean);
  // Deduplicate while preserving order
  return [...new Set(labels)].slice(0, 4);
}

// ─── Scoring ─────────────────────────────────────────────────────────

const MAX_GENRE_SCORE = 800_000; // empirical max aggregate genre tag count
const MAX_MOOD_SCORE  = 200_000;

function computeMatch(
  book:        RawBook,
  genreTagIds: number[],
  moodTagIds:  number[],
  userGenres:  string[],
): number {
  // Normalise tag scores to 0-1
  const gNorm = genreTagIds.length > 0
    ? Math.min(book.genre_score / MAX_GENRE_SCORE, 1.0)
    : 0.5;  // no genre selected → neutral

  const mNorm = moodTagIds.length > 0
    ? Math.min(book.mood_score / MAX_MOOD_SCORE, 1.0)
    : 0.5;

  // Quality: normalise avg_rating (range 2.47-4.82 → 0-1)
  const qualityNorm = (book.average_rating - 2.0) / 3.0;

  // Popularity: log-scale to avoid huge books dominating
  const popNorm = Math.min(Math.log10(Math.max(book.ratings_count, 1)) / 6.0, 1.0);

  const weighted = gNorm * 0.50 + mNorm * 0.25 + qualityNorm * 0.17 + popNorm * 0.08;
  return Math.max(50, Math.round(weighted * 100));
}

// ─── Main query helpers ──────────────────────────────────────────────

function buildTagScoreSubquery(tagIds: number[], alias: string): string {
  if (tagIds.length === 0) return '';
  const list = tagIds.join(',');
  return `
    LEFT JOIN (
      SELECT book_id, SUM(count) AS ${alias}
      FROM book_tags
      WHERE tag_id IN (${list})
      GROUP BY book_id
    ) ${alias}_q ON ${alias}_q.book_id = b.id`;
}

// ─── Public API ──────────────────────────────────────────────────────

export function getRecommendations(req: RecommendRequest): BookResult[] {
  const { genres, moods, maxPages, format } = req;

  // Resolve genre and mood tag IDs
  const genreTagNames = genres.flatMap(g => GENRE_TAG_MAP[g] ?? []);
  const moodTagNames  = moods.flatMap(m => MOOD_TAG_MAP[m]  ?? []);
  const genreTagIds   = resolveTagIds(genreTagNames);
  const moodTagIds    = resolveTagIds(moodTagNames);

  const noGenres = genreTagIds.length === 0;
  const noMoods  = moodTagIds.length  === 0;

  // Build optional subqueries
  const genreJoin = buildTagScoreSubquery(genreTagIds, 'genre_score');
  const moodJoin  = buildTagScoreSubquery(moodTagIds,  'mood_score');

  // Page filter: 900 = slider max, treat as "no limit"
  const pageFilter = maxPages >= 900
    ? ''
    : 'AND (b.pages IS NULL OR b.pages <= @maxPages)';

  // Genre filter: if genres selected, require at least some genre tag match
  const genreFilter = noGenres ? '' : 'AND COALESCE(genre_score_q.genre_score, 0) > 0';

  const sql = `
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
    ${genreJoin}
    ${moodJoin}
    WHERE b.average_rating >= 3.5
      ${pageFilter}
      ${genreFilter}
    ORDER BY
      (
        COALESCE(genre_score_q.genre_score, 0) * 0.5 +
        COALESCE(mood_score_q.mood_score,  0) * 0.3 +
        b.average_rating * 20000 +
        MIN(b.ratings_count, 500000) * 0.01
      ) DESC
    LIMIT 30
  `;

  const raw = db.prepare(sql).all({ maxPages }) as RawBook[];

  // Determine matching moods for each book via per-book tag check
  // (optimised: only run if moods were selected)
  const bookMoodMap = buildBookMoodMap(
    raw.map(r => r.id),
    moods,
    moodTagIds
  );

  // Format results
  const results: BookResult[] = raw.map(book => {
    const rawGenres  = parseJsonArr(book.genres);
    const dispGenres = mapGenreLabels(rawGenres);
    const matchMoods = bookMoodMap.get(book.id) ?? [];
    const match      = computeMatch(book, genreTagIds, moodTagIds, genres);

    return {
      title:          book.title,
      author:         book.authors || 'Unknown',
      genres:         dispGenres,
      moods:          matchMoods,
      pages:          book.pages,
      formats:        inferFormats(book.ratings_count),
      pitch:          makePitch(book.description || ''),
      match,
      average_rating: book.average_rating,
      ratings_count:  book.ratings_count,
      image_url:      book.image_url || '',
      pub_year:       book.pub_year,
    };
  });

  // Deduplicate by title and return top 12
  const seen = new Set<string>();
  return results
    .filter(b => {
      if (seen.has(b.title)) return false;
      seen.add(b.title);
      return true;
    })
    .sort((a, b) => b.match - a.match)
    .slice(0, 12);
}

/** For each book ID, determine which of the user's selected moods it matches */
function buildBookMoodMap(
  bookIds:    number[],
  moods:      string[],
  moodTagIds: number[],
): Map<number, string[]> {
  const map = new Map<number, string[]>();
  if (bookIds.length === 0 || moods.length === 0 || moodTagIds.length === 0) {
    return map;
  }

  // For each book, find which mood-tagged tags it actually has
  const idList = bookIds.join(',');

  for (const mood of moods) {
    const moodTags = resolveTagIds(MOOD_TAG_MAP[mood] ?? []);
    if (moodTags.length === 0) continue;

    const tagList = moodTags.join(',');
    const rows = db.prepare(`
      SELECT DISTINCT book_id
      FROM book_tags
      WHERE book_id IN (${idList})
        AND tag_id IN (${tagList})
        AND count > 50
    `).all() as { book_id: number }[];

    for (const { book_id } of rows) {
      const existing = map.get(book_id) ?? [];
      existing.push(mood);
      map.set(book_id, existing);
    }
  }

  return map;
}

/** Fallback: top-rated popular books when no filters applied */
export function getTopBooks(limit = 12): BookResult[] {
  const rows = db.prepare(`
    SELECT id, title, authors, average_rating, ratings_count,
           pub_year, pages, description, genres, image_url,
           0 AS genre_score, 0 AS mood_score
    FROM books
    WHERE average_rating >= 4.0
    ORDER BY ratings_count DESC
    LIMIT ?
  `).all(limit) as RawBook[];

  return rows.map(book => ({
    title:          book.title,
    author:         book.authors,
    genres:         mapGenreLabels(parseJsonArr(book.genres)),
    moods:          [],
    pages:          book.pages,
    formats:        inferFormats(book.ratings_count),
    pitch:          makePitch(book.description || ''),
    match:          Math.round(70 + (book.average_rating - 4.0) * 15),
    average_rating: book.average_rating,
    ratings_count:  book.ratings_count,
    image_url:      book.image_url || '',
    pub_year:       book.pub_year,
  }));
}
