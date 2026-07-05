/**
 * api/recommend.ts — API client for the SHELF/MATCH backend.
 *
 * In Docker / production: requests go to /api/* which nginx proxies to backend:8000
 * In local dev:           Vite proxies /api/* to http://localhost:8000
 */

import type { RecommendRequest, RecommendResponse } from '../types'

/** POST /api/recommend — fetch book recommendations from the backend. */
export async function recommendBooks(
  payload: RecommendRequest,
): Promise<RecommendResponse> {
  const response = await fetch('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText)
    throw new Error(`API ${response.status}: ${detail}`)
  }

  return response.json() as Promise<RecommendResponse>
}
