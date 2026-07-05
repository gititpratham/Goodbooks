/**
 * index.ts — SHELF/MATCH API Server
 *
 * Start:  npm run dev   (ts-node, for development)
 *         npm start     (compiled JS)
 *
 * Endpoints:
 *   POST /api/recommend         → get book recommendations
 *   GET  /api/recommend/genres  → list genre options
 *   GET  /api/recommend/moods   → list mood options
 *   GET  /api/health            → health check
 */

import express from 'express';
import cors from 'cors';
import path from 'path';
import { createSchema } from './db';
import recommendRouter from './routes/recommend';

const app  = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 3001;

// ─── Middleware ──────────────────────────────────────────────────────
app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'null',           // file:// protocol (opening HTML directly)
  ],
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type'],
  credentials: false,
}));

app.use(express.json());

// Serve the frontend as static files
app.use(express.static(path.join(__dirname, '..', '..', 'frontend')));

// ─── Routes ──────────────────────────────────────────────────────────
app.use('/api/recommend', recommendRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', service: 'SHELF/MATCH API', version: '1.0.0' });
});

// Catch-all: serve frontend for any unmatched route
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'frontend', 'index.html'));
});

// ─── Boot ─────────────────────────────────────────────────────────────
function start() {
  // Ensure schema exists (idempotent)
  createSchema();
  console.log('──────────────────────────────────────────');
  console.log('  SHELF/MATCH API');
  console.log('──────────────────────────────────────────');
  console.log(`  http://localhost:${PORT}`);
  console.log('  Frontend: http://localhost:' + PORT + '/');
  console.log('  Health:   http://localhost:' + PORT + '/api/health');
  console.log('──────────────────────────────────────────');
  console.log('  Run "npm run seed" first if db is empty');
  console.log('──────────────────────────────────────────');
}

app.listen(PORT, () => {
  start();
});

export default app;
