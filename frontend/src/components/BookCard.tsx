/**
 * BookCard.tsx — Single book recommendation card.
 * Displays real data from the API: title, author, rating, cover image,
 * matched genre chips, matched mood chips, publication year, and match %.
 */

import type { BookResult } from '../types'

interface BookCardProps {
  book: BookResult
  rank: number
}

// Fallback cover if image_url is missing or fails to load
const PLACEHOLDER = 'https://via.placeholder.com/160x220/111111/EDEAE0?text=NO+COVER'

export default function BookCard({ book, rank }: BookCardProps) {
  const year      = book.pub_year ? `${book.pub_year}` : 'YEAR UNKNOWN'
  const ratingStr = `★ ${book.average_rating.toFixed(2)}`
  const countStr = book.ratings_count > 1_000_000
    ? `${(book.ratings_count / 1_000_000).toFixed(1)}M ratings`
    : book.ratings_count > 1_000
    ? `${(book.ratings_count / 1_000).toFixed(0)}K ratings`
    : `${book.ratings_count} ratings`

  // Combine genre + mood chips, limit to 5 total
  const chips = [
    ...book.genres.map(g => ({ label: g, type: 'genre' })),
    ...book.moods.map(m => ({ label: m, type: 'mood' })),
  ].slice(0, 5)

  return (
    <div className="card">
      {/* Rank badge (top-left) */}
      <div className="card-rank">#{rank}</div>

      {/* Match percentage stamp (top-right) */}
      <div className="card-match">{book.match}% MATCH</div>

      {/* Cover image */}
      {book.image_url && (
        <div style={{ textAlign: 'center', marginTop: 18, marginBottom: 8 }}>
          <img
            src={book.image_url}
            alt={`Cover of ${book.title}`}
            onError={e => { (e.target as HTMLImageElement).src = PLACEHOLDER }}
            style={{
              width: 80,
              height: 'auto',
              border: '2px solid var(--ink)',
              display: 'inline-block',
            }}
          />
        </div>
      )}

      {/* Title + author */}
      <h3 style={{ marginTop: book.image_url ? 8 : 18 }}>{book.title}</h3>
      <div className="author">by {book.author}</div>

      {/* Description / pitch — show a note if empty */}
      {book.pitch ? (
        <p className="pitch">{book.pitch}</p>
      ) : (
        <p className="pitch" style={{ color: '#888', fontStyle: 'italic' }}>
          No description available in dataset.
        </p>
      )}

      {/* Genre + mood chips */}
      {chips.length > 0 && (
        <div className="tags-row">
          {chips.map(c => (
            <span
              key={c.label}
              className="tag-chip"
              style={c.type === 'mood' ? { background: 'var(--yellow)' } : undefined}
            >
              {c.label}
            </span>
          ))}
        </div>
      )}

      <div className="divider-stamp" />

      {/* Footer: rating / pages / count / year */}
      <div className="card-foot">
        <span>{ratingStr} · {book.pages ? `${book.pages}p` : '?p'} · {countStr}</span>
        <span className="stamp-label">{year}</span>
      </div>
    </div>
  )
}
