import React, { useState, useEffect } from 'react';

// TypeScript Interfaces
interface Book {
  id: number;
  book_id: number;
  title: string;
  authors: string;
  average_rating: number;
  description: string;
  genres: string;
  image_url: string;
  pages: number;
  publish_date: string;
  ratings_count: number;
}

// API Config
const API_BASE = (import.meta.env.VITE_API_URL as string) || 
  `${window.location.protocol}//${window.location.hostname}:8000`;

// Clean serialized string lists: "['fiction', 'fantasy']" -> ["fiction", "fantasy"]
const parseList = (str: string): string[] => {
  if (!str) return [];
  try {
    return str
      .replace(/[\[\]']/g, '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  } catch (e) {
    return [];
  }
};

// Inline SVG Icon Components
const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
);

const CompassIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
);

const SparklesIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 5a7 7 0 0 0-7 7h14a7 7 0 0 0-7-7z"></path><path d="M5 12a7 7 0 0 0 7 7v-14a7 7 0 0 0-7 7z" fill="currentColor" opacity="0.2"></path><path d="M12 2v20M2 12h20" strokeDasharray="3 3"></path></svg>
);

const StarIcon = ({ filled = true }: { filled?: boolean }) => (
  <svg className="rating-star" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
);

const BookOpenIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
);

const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
);

// Fallback cover element if image fails to load
const FallbackCover = ({ title, author }: { title: string; author: string }) => (
  <div className="fallback-cover">
    <div className="fallback-logo">BookVerse</div>
    <div className="fallback-title">{title}</div>
    <div className="fallback-author">{parseList(author)[0] || 'Unknown Author'}</div>
    <div></div>
  </div>
);

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState<'explore' | 'wizard'>('explore');

  // Catalog State
  const [books, setBooks] = useState<Book[]>([]);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedGenre, setSelectedGenre] = useState<string>('');
  const [availableGenres, setAvailableGenres] = useState<string[]>([]);
  const [catalogLoading, setCatalogLoading] = useState<boolean>(false);

  // Book Details Modal State
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [similarBooks, setSimilarBooks] = useState<Book[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState<boolean>(false);
  const [coverErrors, setCoverErrors] = useState<Record<number, boolean>>({});

  // Wizard Recommendation State
  const [wizardGenres, setWizardGenres] = useState<string[]>([]);
  const [wizardKeywords, setWizardKeywords] = useState<string>('');
  const [wizardMinRating, setWizardMinRating] = useState<number>(3.5);
  const [wizardRecommendations, setWizardRecommendations] = useState<Book[]>([]);
  const [wizardLoading, setWizardLoading] = useState<boolean>(false);
  const [wizardAttempted, setWizardAttempted] = useState<boolean>(false);

  // Load catalog on page/filter changes
  useEffect(() => {
    if (activeTab === 'explore') {
      fetchCatalog();
    }
  }, [page, searchQuery, selectedGenre, activeTab]);

  // Load genres list on startup
  useEffect(() => {
    fetchGenresList();
  }, []);

  const fetchCatalog = async () => {
    setCatalogLoading(true);
    try {
      const url = `${API_BASE}/api/books?page=${page}&limit=20&search=${encodeURIComponent(searchQuery)}&genre=${encodeURIComponent(selectedGenre)}`;
      const response = await fetch(url);
      const data = await response.json();
      setBooks(data.books || []);
      setTotalPages(Math.max(1, Math.ceil((data.total || 0) / 20)));
    } catch (e) {
      console.error("Error fetching book catalog:", e);
    } finally {
      setCatalogLoading(false);
    }
  };

  const fetchGenresList = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/genres`);
      const data = await response.json();
      setAvailableGenres(data || []);
    } catch (e) {
      console.error("Error fetching genres list:", e);
    }
  };

  const handleBookClick = async (book: Book) => {
    setSelectedBook(book);
    setLoadingSimilar(true);
    setSimilarBooks([]);
    try {
      const response = await fetch(`${API_BASE}/api/recommend/by-book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: book.book_id, limit: 5 })
      });
      const data = await response.json();
      setSimilarBooks(data.recommendations || []);
    } catch (e) {
      console.error("Error fetching similar books:", e);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const handleImageError = (bookId: number) => {
    setCoverErrors(prev => ({ ...prev, [bookId]: true }));
  };

  // Wizard toggles
  const handleWizardGenreToggle = (genre: string) => {
    setWizardGenres(prev => 
      prev.includes(genre) 
        ? prev.filter(g => g !== genre)
        : [...prev, genre]
    );
  };

  const generateRecommendations = async () => {
    setWizardLoading(true);
    setWizardAttempted(true);
    try {
      const response = await fetch(`${API_BASE}/api/recommend/by-preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          genres: wizardGenres,
          keywords: wizardKeywords,
          min_rating: wizardMinRating,
          limit: 12
        })
      });
      const data = await response.json();
      setWizardRecommendations(data.recommendations || []);
    } catch (e) {
      console.error("Error generating recommendations:", e);
    } finally {
      setWizardLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="logo-container" onClick={() => { setActiveTab('explore'); setPage(1); setSearchQuery(''); setSelectedGenre(''); }}>
          <div className="logo-icon">📚</div>
          <h1 className="logo-text gradient-text">BookVerse</h1>
        </div>
        <nav className="nav-links">
          <button 
            className={`nav-btn ${activeTab === 'explore' ? 'active' : ''}`}
            onClick={() => setActiveTab('explore')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
              <CompassIcon /> Explore Catalog
            </span>
          </button>
          <button 
            className={`nav-btn ${activeTab === 'wizard' ? 'active' : ''}`}
            onClick={() => setActiveTab('wizard')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
              <SparklesIcon /> AI Recommender
            </span>
          </button>
        </nav>
      </header>

      {/* Explore Tab */}
      {activeTab === 'explore' && (
        <section style={{ animation: 'fadeIn 0.5s ease-out' }}>
          <div className="explorer-controls">
            <div className="search-wrapper">
              <span className="search-icon-inline"><SearchIcon /></span>
              <input 
                type="text" 
                className="search-input" 
                placeholder="Search by book title or author..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              />
            </div>
            <select 
              className="filter-select"
              value={selectedGenre}
              onChange={(e) => { setSelectedGenre(e.target.value); setPage(1); }}
            >
              <option value="">All Genres</option>
              {availableGenres.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>

          {catalogLoading ? (
            <div className="loader-container">
              <div className="spinner"></div>
              <p style={{ color: 'var(--text-secondary)' }}>Flipping through pages...</p>
            </div>
          ) : books.length === 0 ? (
            <div className="loader-container">
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem' }}>No books found matching your query.</p>
            </div>
          ) : (
            <>
              <div className="books-grid">
                {books.map(book => {
                  const hasCoverError = coverErrors[book.book_id];
                  return (
                    <div 
                      key={book.book_id} 
                      className="glass-panel book-card"
                      onClick={() => handleBookClick(book)}
                    >
                      <div className="cover-wrapper">
                        {book.image_url && !hasCoverError ? (
                          <img 
                            src={book.image_url} 
                            alt={book.title} 
                            className="book-cover"
                            onError={() => handleImageError(book.book_id)}
                          />
                        ) : (
                          <FallbackCover title={book.title} author={book.authors} />
                        )}
                      </div>
                      <div className="book-info">
                        <div className="book-title" title={book.title}>{book.title}</div>
                        <div className="book-authors">{parseList(book.authors).join(', ')}</div>
                        <div className="book-meta">
                          <div className="rating-container">
                            <StarIcon />
                            <span className="rating-value">{book.average_rating.toFixed(2)}</span>
                          </div>
                          <span className="rating-count">({book.ratings_count.toLocaleString()} ratings)</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              <div className="pagination">
                <button 
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </button>
                <span className="pagination-info">Page {page} of {totalPages}</span>
                <button 
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {/* AI Recommender Tab */}
      {activeTab === 'wizard' && (
        <section className="wizard-section">
          <div className="glass-panel wizard-card">
            <h2 className="wizard-title gradient-text">Book Recommendation Wizard</h2>
            <p className="wizard-subtitle">
              Configure your preferences below and let our content similarity engine match you with your next favorite read.
            </p>

            <div className="form-group">
              <label className="form-label">Which genres interest you? (Select multiple)</label>
              <div className="genre-selector">
                {availableGenres.map(genre => {
                  const isSelected = wizardGenres.includes(genre);
                  return (
                    <span 
                      key={genre}
                      className={`genre-tag ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleWizardGenreToggle(genre)}
                    >
                      {genre}
                    </span>
                  );
                })}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Describe what you are looking for (Mood, keywords, plots, characters)</label>
              <input 
                type="text" 
                className="text-input"
                placeholder="e.g. a cozy mystery set in Britain, futuristic space battle, heartwarming romance with humor"
                value={wizardKeywords}
                onChange={(e) => setWizardKeywords(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Minimum Book Rating</label>
              <div className="slider-container">
                <input 
                  type="range" 
                  min="0.0" 
                  max="5.0" 
                  step="0.1" 
                  className="slider"
                  value={wizardMinRating}
                  onChange={(e) => setWizardMinRating(parseFloat(e.target.value))}
                />
                <span className="slider-value">{wizardMinRating.toFixed(1)}</span>
              </div>
            </div>

            <button 
              className="btn-primary"
              onClick={generateRecommendations}
              disabled={wizardLoading}
            >
              {wizardLoading ? "Aligning stars..." : "Find My Next Book 🪄"}
            </button>
          </div>

          {/* Wizard Recommendations Results */}
          {wizardAttempted && (
            <div style={{ marginTop: '4rem', animation: 'fadeIn 0.5s ease-out' }}>
              <h3 className="section-title">
                <span style={{ color: 'var(--accent-purple)' }}>✨</span> Handpicked for You
              </h3>
              
              {wizardLoading ? (
                <div className="loader-container">
                  <div className="spinner"></div>
                  <p style={{ color: 'var(--text-secondary)' }}>Calculating matching vectors...</p>
                </div>
              ) : wizardRecommendations.length === 0 ? (
                <div className="loader-container">
                  <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem' }}>We couldn't find matches. Try adjusting filters or typing simpler keywords!</p>
                </div>
              ) : (
                <div className="books-grid" style={{ marginTop: '2rem' }}>
                  {wizardRecommendations.map(book => {
                    const hasCoverError = coverErrors[book.book_id];
                    return (
                      <div 
                        key={book.book_id} 
                        className="glass-panel book-card"
                        onClick={() => handleBookClick(book)}
                      >
                        <div className="cover-wrapper">
                          {book.image_url && !hasCoverError ? (
                            <img 
                              src={book.image_url} 
                              alt={book.title} 
                              className="book-cover"
                              onError={() => handleImageError(book.book_id)}
                            />
                          ) : (
                            <FallbackCover title={book.title} author={book.authors} />
                          )}
                        </div>
                        <div className="book-info">
                          <div className="book-title" title={book.title}>{book.title}</div>
                          <div className="book-authors">{parseList(book.authors).join(', ')}</div>
                          <div className="book-meta">
                            <div className="rating-container">
                              <StarIcon />
                              <span className="rating-value">{book.average_rating.toFixed(2)}</span>
                            </div>
                            <span className="rating-count">({book.ratings_count.toLocaleString()})</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Book Details Modal */}
      {selectedBook && (
        <div className="modal-overlay" onClick={() => setSelectedBook(null)}>
          <div className="glass-panel modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setSelectedBook(null)}>
              <XIcon />
            </button>

            <div className="book-detail-layout">
              <div className="cover-wrapper-detail">
                {selectedBook.image_url && !coverErrors[selectedBook.book_id] ? (
                  <img 
                    src={selectedBook.image_url} 
                    alt={selectedBook.title} 
                    onError={() => handleImageError(selectedBook.book_id)}
                  />
                ) : (
                  <FallbackCover title={selectedBook.title} author={selectedBook.authors} />
                )}
              </div>

              <div className="book-detail-info">
                <h2 className="book-detail-title">{selectedBook.title}</h2>
                <div className="book-detail-authors">by {parseList(selectedBook.authors).join(', ')}</div>
                
                {selectedBook.genres && (
                  <div className="book-detail-tags">
                    {parseList(selectedBook.genres).map(g => (
                      <span key={g} className="detail-tag">{g}</span>
                    ))}
                  </div>
                )}

                <div className="book-detail-stats">
                  <div className="stat-item">
                    <span className="stat-label">Rating</span>
                    <span className="stat-value rating"><StarIcon /> {selectedBook.average_rating.toFixed(2)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Ratings Count</span>
                    <span className="stat-value">{selectedBook.ratings_count.toLocaleString()}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Pages</span>
                    <span className="stat-value">{selectedBook.pages || 'N/A'}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Published</span>
                    <span className="stat-value">{selectedBook.publish_date || 'N/A'}</span>
                  </div>
                </div>

                <h3 className="book-detail-desc-title">Synopsis</h3>
                <p className="book-detail-desc">{selectedBook.description || "No synopsis available for this book."}</p>
              </div>
            </div>

            {/* Recommendations */}
            <div className="similar-books-section">
              <h3 className="similar-books-title">Readers Also Enjoyed (Similar Books)</h3>
              {loadingSimilar ? (
                <div className="loader-container" style={{ padding: '2rem 0' }}>
                  <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Mapping similarity vectors...</p>
                </div>
              ) : similarBooks.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No similar books found.</p>
              ) : (
                <div className="similar-books-grid">
                  {similarBooks.map(simBook => {
                    const simCoverError = coverErrors[simBook.book_id];
                    return (
                      <div 
                        key={simBook.book_id} 
                        className="glass-panel book-card"
                        style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                        onClick={() => handleBookClick(simBook)}
                      >
                        <div className="cover-wrapper" style={{ marginBottom: '0.5rem' }}>
                          {simBook.image_url && !simCoverError ? (
                            <img 
                              src={simBook.image_url} 
                              alt={simBook.title} 
                              className="book-cover"
                              onError={() => handleImageError(simBook.book_id)}
                            />
                          ) : (
                            <FallbackCover title={simBook.title} author={simBook.authors} />
                          )}
                        </div>
                        <div className="book-title" style={{ fontSize: '0.85rem', fontWeight: 600, WebkitLineClamp: 1 }} title={simBook.title}>
                          {simBook.title}
                        </div>
                        <div className="book-meta" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                          <div className="rating-container">
                            <StarIcon />
                            <span>{simBook.average_rating.toFixed(1)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
