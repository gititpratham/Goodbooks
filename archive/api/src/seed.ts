/**
 * seed.ts — CSV → SQLite seeder
 *
 * Run ONCE before starting the server:
 *   npm run seed
 *
 * Sources:
 *   books_enriched.csv  → books table   (pages, description, genres, ratings)
 *   tags.csv            → tags table
 *   book_tags.csv       → book_tags table  (999k rows, streamed in batches)
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { parse } from 'csv-parse/sync';
import db, { createSchema } from './db';

// ─── Paths ──────────────────────────────────────────────────────────
const ROOT         = path.join(__dirname, '..', '..'); // goodbooks/
const ENRICHED_CSV = path.join(ROOT, 'backend', 'data', 'books_enriched.csv');
const TAGS_CSV     = path.join(ROOT, 'db', 'goodbooks10', 'tags.csv');
const BOOK_TAGS_CSV= path.join(ROOT, 'db', 'goodbooks10', 'book_tags.csv');

const BATCH_SIZE = 5_000; // rows per transaction for book_tags

// ─── Helpers ────────────────────────────────────────────────────────

/** Parse Python list strings like "['a', 'b']" → ['a','b'] */
function parsePyList(raw: string | undefined): string[] {
  if (!raw || raw.trim() === '' || raw.trim() === '[]') return [];
  try {
    // Replace Python single quotes with JSON double quotes
    const json = raw
      .replace(/'/g, '"')
      .replace(/\bNone\b/g, 'null')
      .replace(/\bTrue\b/g, 'true')
      .replace(/\bFalse\b/g, 'false');
    const parsed = JSON.parse(json);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    // Fallback: naive comma-split
    return raw
      .replace(/^\[|\]$/g, '')
      .split(',')
      .map(s => s.trim().replace(/^['"]|['"]$/g, ''))
      .filter(Boolean);
  }
}

/** Capitalise first letter of each word */
function titleCase(s: string): string {
  return s.replace(/\b\w/g, c => c.toUpperCase());
}

function log(msg: string) { process.stdout.write(`  ${msg}\n`); }
function sep() { console.log('─'.repeat(56)); }

// ─── Step 1: Schema ──────────────────────────────────────────────────
sep();
console.log('  GOODBOOKS — SQLite Seeder');
sep();
createSchema();
log('Schema created / verified ✓');

// ─── Step 2: books ───────────────────────────────────────────────────
log('');
log('[1/3] Seeding books from books_enriched.csv ...');

const existingCount = (db.prepare('SELECT COUNT(*) as c FROM books').get() as { c: number }).c;
if (existingCount > 0) {
  log(`  Already seeded (${existingCount.toLocaleString()} rows). Skipping.`);
} else {
  const rawCSV = fs.readFileSync(ENRICHED_CSV, 'utf-8');
  const rows = parse(rawCSV, { columns: true, skip_empty_lines: true, relax_quotes: true });

  const insertBook = db.prepare(`
    INSERT OR REPLACE INTO books
      (id, title, authors, all_authors, average_rating, ratings_count,
       pub_year, pages, description, genres, image_url, language_code)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertAll = db.transaction((records: typeof rows) => {
    for (const r of records) {
      const authorsList = parsePyList(r.authors || r.authors_2);
      const firstAuthor = authorsList[0] || r.authors?.replace(/^\[|\]$/g,'').trim() || 'Unknown';
      const genresList  = parsePyList(r.genres);
      const pubYear     = r.original_publication_year ? parseInt(r.original_publication_year) : null;
      const pages       = r.pages ? parseInt(r.pages) : null;
      const desc        = (r.description || '').slice(0, 600);
      const rating      = parseFloat(r.average_rating) || 0;
      const ratingsCnt  = parseInt(r.ratings_count) || 0;

      insertBook.run(
        parseInt(r.book_id),
        r.title,
        firstAuthor,
        JSON.stringify(authorsList),
        rating,
        ratingsCnt,
        pubYear,
        pages,
        desc,
        JSON.stringify(genresList),
        r.image_url || '',
        r.language_code || 'eng'
      );
    }
  });

  insertAll(rows);
  log(`  Inserted ${rows.length.toLocaleString()} books ✓`);
}

// ─── Step 3: tags ────────────────────────────────────────────────────
log('');
log('[2/3] Seeding tags from tags.csv ...');

const existingTags = (db.prepare('SELECT COUNT(*) as c FROM tags').get() as { c: number }).c;
if (existingTags > 0) {
  log(`  Already seeded (${existingTags.toLocaleString()} tags). Skipping.`);
} else {
  const tagsRaw  = fs.readFileSync(TAGS_CSV, 'utf-8');
  const tagRows  = parse(tagsRaw, { columns: true, skip_empty_lines: true });
  const insertTag = db.prepare('INSERT OR IGNORE INTO tags (tag_id, tag_name) VALUES (?, ?)');
  const insertAllTags = db.transaction((records: typeof tagRows) => {
    for (const r of records) insertTag.run(parseInt(r.tag_id), r.tag_name);
  });
  insertAllTags(tagRows);
  log(`  Inserted ${tagRows.length.toLocaleString()} tags ✓`);
}

// ─── Step 4: book_tags (streamed) ────────────────────────────────────
log('');
log('[3/3] Seeding book_tags from book_tags.csv (999k rows, streaming) ...');

const existingBT = (db.prepare('SELECT COUNT(*) as c FROM book_tags').get() as { c: number }).c;
if (existingBT > 0) {
  log(`  Already seeded (${existingBT.toLocaleString()} rows). Skipping.`);
  sep();
  log('Seeding complete! Run: npm run dev');
  sep();
  process.exit(0);
}

const insertBT = db.prepare('INSERT OR IGNORE INTO book_tags (book_id, tag_id, count) VALUES (?,?,?)');
const batchInsert = db.transaction((batch: [number, number, number][]) => {
  for (const [bid, tid, cnt] of batch) insertBT.run(bid, tid, cnt);
});

(async () => {
  const stream = fs.createReadStream(BOOK_TAGS_CSV);
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let firstLine = true;
  let batch: [number, number, number][] = [];
  let total = 0;

  for await (const line of rl) {
    if (firstLine) { firstLine = false; continue; } // skip header
    if (!line.trim()) continue;

    const [gid, tid, cnt] = line.split(',');
    batch.push([parseInt(gid), parseInt(tid), parseInt(cnt)]);

    if (batch.length >= BATCH_SIZE) {
      batchInsert(batch);
      total += batch.length;
      batch = [];
      if (total % 100_000 === 0) log(`  ${total.toLocaleString()} rows inserted ...`);
    }
  }

  if (batch.length) {
    batchInsert(batch);
    total += batch.length;
  }

  log(`  Inserted ${total.toLocaleString()} book_tag associations ✓`);
  sep();
  log('Seeding complete! Run: npm run dev');
  sep();
})();
