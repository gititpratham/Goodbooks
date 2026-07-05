/**
 * routes/recommend.ts — POST /api/recommend
 */

import { Router, Request, Response } from 'express';
import { getRecommendations, getTopBooks, RecommendRequest } from '../recommender';

const router = Router();

// ── POST /api/recommend ──────────────────────────────────────────────
router.post('/', (req: Request, res: Response) => {
  const { genres, moods, maxPages, format } = req.body as Partial<RecommendRequest>;

  // Validate / normalise inputs
  const cleanGenres  = Array.isArray(genres) ? genres.map(String)  : [];
  const cleanMoods   = Array.isArray(moods)  ? moods.map(String)   : [];
  const cleanPages   = typeof maxPages === 'number' && maxPages > 0 ? maxPages : 900;
  const cleanFormat  = typeof format  === 'string'  ? format  : 'any';

  try {
    const books = (cleanGenres.length === 0 && cleanMoods.length === 0)
      ? getTopBooks(12)
      : getRecommendations({
          genres:   cleanGenres,
          moods:    cleanMoods,
          maxPages: cleanPages,
          format:   cleanFormat,
        });

    res.json({
      books,
      count: books.length,
      query: {
        genres:   cleanGenres,
        moods:    cleanMoods,
        maxPages: cleanPages,
        format:   cleanFormat,
      },
    });
  } catch (err) {
    console.error('[/api/recommend] Error:', err);
    res.status(500).json({ error: 'Recommendation engine error', details: String(err) });
  }
});

// ── GET /api/recommend/genres — available genre options ──────────────
router.get('/genres', (_req: Request, res: Response) => {
  res.json([
    'Fantasy', 'Sci-Fi', 'Mystery', 'Romance',
    'Literary Fiction', 'Horror', 'Non-Fiction', 'Thriller', 'Historical',
  ]);
});

// ── GET /api/recommend/moods — available mood options ────────────────
router.get('/moods', (_req: Request, res: Response) => {
  res.json([
    'Cozy', 'Dark & Twisty', 'Fast-Paced', 'Slow Burn',
    'Thought-Provoking', 'Escapist', 'Heartwarming', 'Unsettling',
  ]);
});

export default router;
