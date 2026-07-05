/** Shared TypeScript types across the frontend. */

export interface BookResult {
  title: string
  author: string
  genres: string[]
  moods: string[]
  pages: number | null
  formats: string[]
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
  maxPages: number
  format: string
}

export interface RecommendResponse {
  books: BookResult[]
  count: number
  query: RecommendRequest
}
