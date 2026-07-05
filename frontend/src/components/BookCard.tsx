/**
 * BookCard.tsx — Single book recommendation card.
 * Preserves the original visual design: rank badge, match stamp, pitch, tags.
 */

import type { BookResult } from '../types'

interface BookCardProps {
  book: BookResult
  rank: number
}

export default function BookCard({ book, rank }: BookCardProps) {
  const pagesLabel  = book.pages ? `${book.pages} PP` : 'LENGTH UNKNOWN'
  const ratingLabel = book.average_rating
    ? `★ ${book.average_rating.toFixed(2)}`
    : ''
  const footLeft    = [pagesLabel, ratingLabel].filter(Boolean).join(' · ')
  const footRight   = book.formats.join(' / ')

  return (
    <div className="card">
      <div className="card-rank">#{rank}</div>
      <div className="card-match">{book.match}% MATCH</div>
      <div className="stamp-label">ISSUED FROM CATALOG</div>

      <h3>{book.title}</h3>
      <div className="author">by {book.author}</div>
      <p className="pitch">{book.pitch || '—'}</p>

      <div className="tags-row">
        {book.genres.map(g => (
          <span key={g} className="tag-chip">{g}</span>
        ))}
        {book.moods.map(m => (
          <span key={m} className="tag-chip">{m}</span>
        ))}
      </div>

      <div className="divider-stamp" />

      <div className="card-foot">
        <span>{footLeft}</span>
        <span>{footRight}</span>
      </div>
    </div>
  )
}
