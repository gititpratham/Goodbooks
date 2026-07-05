/** Static option lists matching the backend tag map keys. */

export const GENRES: readonly string[] = [
  'Fantasy',
  'Sci-Fi',
  'Mystery',
  'Romance',
  'Literary Fiction',
  'Horror',
  'Non-Fiction',
  'Thriller',
  'Historical',
  'Young Adult',
  'Graphic Novel',
]

export const MOODS: readonly string[] = [
  'Cozy',
  'Dark & Twisty',
  'Fast-Paced',
  'Slow Burn',
  'Thought-Provoking',
  'Escapist',
  'Heartwarming',
  'Unsettling',
]

export const PUB_ERAS: readonly { value: string; label: string }[] = [
  { value: 'any',     label: 'Any Era'                   },
  { value: 'recent',  label: 'Recent  (2000 → now)'      },
  { value: 'classic', label: 'Classic (pre-1980)'         },
]

export const DEFAULT_MIN_RATING = 3.5
export const DEFAULT_MAX_PAGES  = 900   // 900 = "no limit" sentinel
