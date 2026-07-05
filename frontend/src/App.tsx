/**
 * App.tsx — Main application component.
 * Form: Genre (multi), Mood (multi), Min Rating (slider), Max Pages (slider), Pub Era (tiles).
 * Results: top-3 or all ≥90% match, pulled live from the FastAPI backend.
 */

import { useState, useRef } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import TileGroup from './components/TileGroup'
import LengthSlider from './components/LengthSlider'
import RatingSlider from './components/RatingSlider'
import BookCard from './components/BookCard'
import { GENRES, MOODS, PUB_ERAS, DEFAULT_MIN_RATING, DEFAULT_MAX_PAGES } from './constants'
import { recommendBooks } from './api/recommend'
import type { BookResult, RecommendRequest } from './types'

export default function App() {
  // ── Form state ──────────────────────────────────────────────────────────────
  const [selectedGenres, setSelectedGenres] = useState<Set<string>>(new Set())
  const [selectedMoods,  setSelectedMoods]  = useState<Set<string>>(new Set())
  const [minRating, setMinRating]           = useState<number>(DEFAULT_MIN_RATING)
  const [maxPages,  setMaxPages]            = useState<number>(DEFAULT_MAX_PAGES)
  const [pubEra,    setPubEra]              = useState<string>('any')

  // ── Results state ───────────────────────────────────────────────────────────
  const [results,   setResults]   = useState<BookResult[] | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [lastReq,   setLastReq]   = useState<RecommendRequest | null>(null)

  const resultsRef = useRef<HTMLDivElement>(null)

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const toggleMulti = (set: Set<string>, val: string) => {
    const next = new Set(set)
    next.has(val) ? next.delete(val) : next.add(val)
    return next
  }

  const handlePubEra = (val: string) => {
    // radio-style: clicking the already-selected one deselects back to 'any'
    setPubEra(prev => (prev === val ? 'any' : val))
  }

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const req: RecommendRequest = {
      genres:    Array.from(selectedGenres),
      moods:     Array.from(selectedMoods),
      minRating,
      maxPages,
      pubEra:    pubEra as 'any' | 'recent' | 'classic',
    }
    setLastReq(req)

    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)

    try {
      const res = await recommendBooks(req)
      setResults(res.books)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  // ── Empty / loading state ───────────────────────────────────────────────────
  const renderState = () => {
    if (loading) return (
      <div className="empty-state" style={{ borderStyle: 'solid' }}>
        <div className="display" style={{ fontSize: 14, letterSpacing: '0.14em' }}>
          ◌ &nbsp; SEARCHING CATALOG &nbsp; ◌
        </div>
        <p style={{ marginTop: 10, fontSize: 12, color: '#555' }}>
          Cross-referencing {lastReq?.genres.length || 0} genre(s)
          · {lastReq?.moods.length || 0} mood(s)
          · min ★{lastReq?.minRating.toFixed(1)}
        </p>
      </div>
    )

    if (error) return (
      <div className="empty-state">
        <div className="display">CATALOG OFFLINE</div>
        <p style={{ marginTop: 10, fontSize: 12 }}>
          Could not reach the API.<br />{error}
        </p>
      </div>
    )

    if (results && results.length === 0) return (
      <div className="empty-state">
        <div className="display">NO MATCHES ON FILE</div>
        <p>Try loosening your filters (lower min-rating, pick more genres).</p>
      </div>
    )

    return null
  }

  const pubEraSet = new Set([pubEra].filter(v => v !== 'any'))

  return (
    <>
      <Header />
      <Hero />

      <main>
        <form id="intake-form" onSubmit={handleSubmit}>

          {/* 01 — Genre */}
          <fieldset>
            <legend>Genre</legend>
            <div className="section-label">
              <span className="num">01</span>
              <h2>Genre</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">
                Pick as many as apply <span className="field-hint">— multiple select</span>
              </div>
              <TileGroup
                options={GENRES}
                selected={selectedGenres}
                onToggle={val => setSelectedGenres(toggleMulti(selectedGenres, val))}
                mode="multi"
                group="genre"
              />
            </div>
          </fieldset>

          {/* 02 — Mood */}
          <fieldset>
            <legend>Mood</legend>
            <div className="section-label">
              <span className="num">02</span>
              <h2>Mood</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">
                What headspace are you reading for? <span className="field-hint">— multiple select</span>
              </div>
              <TileGroup
                options={MOODS}
                selected={selectedMoods}
                onToggle={val => setSelectedMoods(toggleMulti(selectedMoods, val))}
                mode="multi"
                group="mood"
              />
            </div>
          </fieldset>

          {/* 03 — Min Rating */}
          <fieldset>
            <legend>Minimum Rating</legend>
            <div className="section-label">
              <span className="num">03</span>
              <h2>Min Rating</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">Only show books rated at least</div>
              <RatingSlider value={minRating} onChange={setMinRating} />
            </div>
          </fieldset>

          {/* 04 — Max Length */}
          <fieldset>
            <legend>Length</legend>
            <div className="section-label">
              <span className="num">04</span>
              <h2>Length</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">
                Max page count <span className="field-hint">— drag right for no limit</span>
              </div>
              <LengthSlider value={maxPages} onChange={setMaxPages} />
            </div>
          </fieldset>

          {/* 05 — Publication Era */}
          <fieldset>
            <legend>Publication Era</legend>
            <div className="section-label">
              <span className="num">05</span>
              <h2>Era</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">
                When was it published? <span className="field-hint">— pick one (optional)</span>
              </div>
              <TileGroup
                options={PUB_ERAS.map(e => e.label)}
                selected={new Set(PUB_ERAS.filter(e => pubEraSet.has(e.value)).map(e => e.label))}
                onToggle={label => {
                  const era = PUB_ERAS.find(e => e.label === label)
                  if (era) handlePubEra(era.value)
                }}
                mode="single"
                group="pubEra"
              />
            </div>
          </fieldset>

          {/* Submit */}
          <div className="submit-row">
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Searching…' : 'Find My Book →'}
            </button>
            <div className="selection-count">
              <b>{selectedGenres.size}</b> genres · <b>{selectedMoods.size}</b> moods selected
            </div>
          </div>
        </form>

        <div style={{ height: 64 }} />

        {/* Results */}
        <div
          id="results"
          className={loading || error || results ? 'show' : ''}
          ref={resultsRef}
        >
          <div className="results-head">
            <h2>Your Shortlist</h2>
            <div className="results-meta">
              {selectedGenres.size > 0 ? Array.from(selectedGenres).join(', ') : 'ANY GENRE'}
              {' · '}
              {selectedMoods.size > 0 ? Array.from(selectedMoods).join(', ') : 'ANY MOOD'}
              {' · '}
              MIN ★{minRating.toFixed(1)}
              {maxPages < 900 ? ` · MAX ${maxPages}PP` : ''}
            </div>
          </div>

          <div className="cards">
            {renderState()}
            {results && !loading && !error &&
              results.map((book, i) => (
                <BookCard key={`${book.title}-${i}`} book={book} rank={i + 1} />
              ))}
          </div>
        </div>
      </main>

      <footer>
        SHELF/MATCH — BOOK RECOMMENDATION ENGINE · POWERED BY GOODBOOKS-10K
      </footer>
    </>
  )
}
