/** Shared TypeScript types — mirrors Python Pydantic models exactly. */

export interface BookResult {
  title: string
  author: string
  genres: string[]
  moods: string[]
  pitch: string
  match: number
  average_rating: number
  ratings_count: number
  image_url: string
  pub_year: number | null
}

export interface RecommendRequest {
  genres: string[]
  moods: string[]
  minRating: number
  maxPages: number
  pubEra: 'any' | 'recent' | 'classic'
}

export interface RecommendResponse {
  books: BookResult[]
  count: number
  query: RecommendRequest
}
