/**
 * App.tsx — Main application component.
 * Manages form state, handles submission, calls API, and renders results.
 */

import { useState, useRef } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import TileGroup from './components/TileGroup'
import LengthSlider from './components/LengthSlider'
import BookCard from './components/BookCard'
import { GENRES, MOODS, FORMATS, DEFAULT_MAX_PAGES } from './constants'
import { recommendBooks } from './api/recommend'
import type { BookResult } from './types'

export default function App() {
  // ── Form State ──
  const [selectedGenres, setSelectedGenres] = useState<Set<string>>(new Set())
  const [selectedMoods, setSelectedMoods]   = useState<Set<string>>(new Set())
  const [selectedFormat, setSelectedFormat] = useState<Set<string>>(new Set())
  const [maxPages, setMaxPages]             = useState<number>(DEFAULT_MAX_PAGES)

  // ── Results State ──
  const [results, setResults] = useState<BookResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [lastQuery, setLastQuery] = useState({ genres: 0, moods: 0, pages: 0 })

  const resultsRef = useRef<HTMLDivElement>(null)

  // ── Handlers ──
  const toggleSet = (set: Set<string>, val: string, multi: boolean = true) => {
    const next = new Set(multi ? set : [])
    if (next.has(val)) {
      next.delete(val)
    } else {
      next.add(val)
    }
    return next
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setLastQuery({ genres: selectedGenres.size, moods: selectedMoods.size, pages: maxPages })

    // Scroll to results area immediately so loading state is visible
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)

    try {
      const formatArr = Array.from(selectedFormat)
      const res = await recommendBooks({
        genres: Array.from(selectedGenres),
        moods: Array.from(selectedMoods),
        maxPages: maxPages,
        format: formatArr.length > 0 ? formatArr[0] : 'any',
      })
      setResults(res.books)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Unknown error occurred.')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  // ── Render Helpers ──
  const renderEmptyState = () => {
    if (loading) {
      return (
        <div className="empty-state" style={{ borderStyle: 'solid' }}>
          <div className="display" style={{ fontSize: 16, letterSpacing: '0.12em' }}>
            ◌ &nbsp; SEARCHING CATALOG &nbsp; ◌
          </div>
          <p style={{ marginTop: 10, fontSize: 12, color: '#555' }}>
            Cross-referencing {lastQuery.genres || 'all'} genre{lastQuery.genres !== 1 ? 's' : ''}
            {lastQuery.moods ? ` · ${lastQuery.moods} mood${lastQuery.moods !== 1 ? 's' : ''}` : ''}
            {' '}· max {lastQuery.pages} pp
          </p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="empty-state">
          <div className="display">CATALOG OFFLINE</div>
          <p style={{ marginTop: 10, fontSize: 12 }}>
            Could not connect to the API.<br />
            {error}
          </p>
        </div>
      )
    }

    if (results && results.length === 0) {
      return (
        <div className="empty-state">
          <div className="display">NO MATCHES ON FILE</div>
          <p>Loosen a filter and resubmit the form.</p>
        </div>
      )
    }

    return null
  }

  return (
    <>
      <Header />
      <Hero />

      <main>
        <form id="intake-form" onSubmit={handleSubmit}>
          {/* Genre */}
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
                onToggle={(val) => setSelectedGenres(toggleSet(selectedGenres, val, true))}
                mode="multi"
                group="genre"
              />
            </div>
          </fieldset>

          {/* Mood */}
          <fieldset>
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
                onToggle={(val) => setSelectedMoods(toggleSet(selectedMoods, val, true))}
                mode="multi"
                group="mood"
              />
            </div>
          </fieldset>

          {/* Length */}
          <fieldset>
            <div className="section-label">
              <span className="num">03</span>
              <h2>Length</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">Max page count you'll tolerate</div>
              <LengthSlider value={maxPages} onChange={setMaxPages} />
            </div>
          </fieldset>

          {/* Format */}
          <fieldset>
            <div className="section-label">
              <span className="num">04</span>
              <h2>Format</h2>
              <span className="rule" />
            </div>
            <div className="field-block">
              <div className="field-title">
                How will you consume it? <span className="field-hint">— pick one</span>
              </div>
              <TileGroup
                options={FORMATS}
                selected={selectedFormat}
                onToggle={(val) => setSelectedFormat(toggleSet(selectedFormat, val, false))}
                mode="single"
                group="format"
              />
            </div>
          </fieldset>

          {/* Submit */}
          <div className="submit-row">
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Searching...' : 'Find My Book →'}
            </button>
            <div className="selection-count">
              <b>{selectedGenres.size}</b> genres · <b>{selectedMoods.size}</b> moods selected
            </div>
          </div>
        </form>

        <div style={{ height: 64 }} />

        {/* Results Area */}
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
              UNDER {maxPages}PP
            </div>
          </div>

          <div className="cards">
            {renderEmptyState()}
            {results && !loading && !error &&
              results.map((book, i) => (
                <BookCard key={book.title + i} book={book} rank={i + 1} />
              ))}
          </div>
        </div>
      </main>

      <footer>
        SHELF/MATCH — A DEMO RECOMMENDATION FRONTEND · CATALOG DATA IS SAMPLE ONLY
      </footer>
    </>
  )
}
