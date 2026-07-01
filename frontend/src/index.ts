// TypeScript interfaces
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

// Configuration
const API_BASE = (window as any).VITE_API_URL || 
  `${window.location.protocol}//${window.location.hostname}:8000`;

// Global State
let activeTab: 'explore' | 'wizard' = 'explore';
let currentPage = 1;
let totalPages = 1;
let searchQuery = '';
let selectedGenre = '';
let wizardSelectedGenres: string[] = [];
let allGenres: string[] = [];

// DOM Elements Cache
const logoHome = document.getElementById('logo-home') as HTMLElement;
const tabExplore = document.getElementById('tab-explore') as HTMLButtonElement;
const tabWizard = document.getElementById('tab-wizard') as HTMLButtonElement;
const sectionExplore = document.getElementById('section-explore') as HTMLElement;
const sectionWizard = document.getElementById('section-wizard') as HTMLElement;

const catalogSearch = document.getElementById('catalog-search') as HTMLInputElement;
const catalogGenreFilter = document.getElementById('catalog-genre-filter') as HTMLSelectElement;
const catalogLoader = document.getElementById('catalog-loader') as HTMLElement;
const catalogGrid = document.getElementById('catalog-grid') as HTMLElement;
const catalogPagination = document.getElementById('catalog-pagination') as HTMLElement;
const paginationPrev = document.getElementById('pagination-prev') as HTMLButtonElement;
const paginationNext = document.getElementById('pagination-next') as HTMLButtonElement;
const paginationInfo = document.getElementById('pagination-info') as HTMLElement;

const wizardGenreSelector = document.getElementById('wizard-genre-selector') as HTMLElement;
const wizardKeywords = document.getElementById('wizard-keywords') as HTMLInputElement;
const wizardRatingSlider = document.getElementById('wizard-rating-slider') as HTMLInputElement;
const wizardRatingVal = document.getElementById('wizard-rating-val') as HTMLElement;
const wizardSubmitBtn = document.getElementById('wizard-submit-btn') as HTMLButtonElement;
const wizardResultsContainer = document.getElementById('wizard-results-container') as HTMLElement;
const wizardLoader = document.getElementById('wizard-loader') as HTMLElement;
const wizardGrid = document.getElementById('wizard-grid') as HTMLElement;

const bookModal = document.getElementById('book-modal') as HTMLElement;
const modalCloseBtn = document.getElementById('modal-close-btn') as HTMLButtonElement;
const modalCoverContainer = document.getElementById('modal-cover-container') as HTMLElement;
const modalTitle = document.getElementById('modal-title') as HTMLElement;
const modalAuthors = document.getElementById('modal-authors') as HTMLElement;
const modalTags = document.getElementById('modal-tags') as HTMLElement;
const modalRating = document.getElementById('modal-rating') as HTMLElement;
const modalRatingsCount = document.getElementById('modal-ratings-count') as HTMLElement;
const modalPages = document.getElementById('modal-pages') as HTMLElement;
const modalPublished = document.getElementById('modal-published') as HTMLElement;
const modalDescription = document.getElementById('modal-description') as HTMLElement;
const similarLoader = document.getElementById('similar-loader') as HTMLElement;
const similarGrid = document.getElementById('similar-grid') as HTMLElement;

// Utility functions
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

const createFallbackCoverHTML = (title: string, authorStr: string): string => {
  const author = parseList(authorStr)[0] || 'Unknown Author';
  return `
    <div class="fallback-cover">
      <div class="fallback-logo">BookVerse</div>
      <div class="fallback-title">${title}</div>
      <div class="fallback-author">${author}</div>
      <div></div>
    </div>
  `;
};

// DOM Builders
function createBookCard(book: Book, isMini = false): HTMLElement {
  const card = document.createElement('div');
  card.className = 'glass-panel book-card';
  if (isMini) {
    card.style.padding = '0.5rem';
    card.style.fontSize = '0.85rem';
  }

  // Cover image / fallback
  const coverHTML = book.image_url 
    ? `<img src="${book.image_url}" alt="${book.title}" class="book-cover">`
    : createFallbackCoverHTML(book.title, book.authors);

  card.innerHTML = `
    <div class="cover-wrapper" style="${isMini ? 'margin-bottom: 0.5rem;' : ''}">
      ${coverHTML}
    </div>
    <div class="book-info">
      <div class="book-title" style="${isMini ? 'font-size: 0.85rem; font-weight: 600; -webkit-line-clamp: 1;' : ''}" title="${book.title}">
        ${book.title}
      </div>
      ${isMini ? '' : `<div class="book-authors">${parseList(book.authors).join(', ')}</div>`}
      <div class="book-meta" style="${isMini ? 'font-size: 0.75rem; margin-top: 0.25rem;' : ''}">
        <div class="rating-container">
          <svg class="rating-star" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          <span class="rating-value">${book.average_rating.toFixed(isMini ? 1 : 2)}</span>
        </div>
        ${isMini ? '' : `<span class="rating-count">(${book.ratings_count.toLocaleString()})</span>`}
      </div>
    </div>
  `;

  // Attach image load error handler if image_url exists
  if (book.image_url) {
    const img = card.querySelector('.book-cover') as HTMLImageElement;
    if (img) {
      img.addEventListener('error', () => {
        const wrapper = card.querySelector('.cover-wrapper') as HTMLElement;
        wrapper.innerHTML = createFallbackCoverHTML(book.title, book.authors);
      });
    }
  }

  // Open modal click handler
  card.addEventListener('click', () => {
    openDetailsModal(book);
  });

  return card;
}

// Logic: Navigation
function switchTab(tab: 'explore' | 'wizard') {
  activeTab = tab;
  if (tab === 'explore') {
    tabExplore.classList.add('active');
    tabWizard.classList.remove('active');
    sectionExplore.style.display = 'block';
    sectionWizard.style.display = 'none';
    fetchCatalog();
  } else {
    tabExplore.classList.remove('active');
    tabWizard.classList.add('active');
    sectionExplore.style.display = 'none';
    sectionWizard.style.display = 'block';
    renderWizardGenres();
  }
}

// Logic: API fetch & rendering
async function fetchCatalog() {
  catalogLoader.style.display = 'flex';
  catalogGrid.style.display = 'none';
  catalogPagination.style.display = 'none';

  try {
    const url = `${API_BASE}/api/books?page=${currentPage}&limit=20&search=${encodeURIComponent(searchQuery)}&genre=${encodeURIComponent(selectedGenre)}`;
    const res = await fetch(url);
    const data = await res.json();
    
    catalogGrid.innerHTML = '';
    const booksList: Book[] = data.books || [];
    
    if (booksList.length === 0) {
      catalogGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 4rem 0; font-size: 1.2rem;">No books found matching your query.</div>';
      catalogGrid.style.display = 'block';
    } else {
      booksList.forEach(book => {
        catalogGrid.appendChild(createBookCard(book));
      });
      catalogGrid.style.display = 'grid';
      
      totalPages = Math.max(1, Math.ceil((data.total || 0) / 20));
      paginationInfo.textContent = `Page ${currentPage} of ${totalPages}`;
      paginationPrev.disabled = currentPage === 1;
      paginationNext.disabled = currentPage === totalPages;
      catalogPagination.style.display = 'flex';
    }
  } catch (e) {
    console.error("Error loading catalog:", e);
    catalogGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--accent-pink); padding: 4rem 0;">Error loading books. Please verify that the API is running.</div>';
    catalogGrid.style.display = 'block';
  } finally {
    catalogLoader.style.display = 'none';
  }
}

async function fetchGenres() {
  try {
    const res = await fetch(`${API_BASE}/api/genres`);
    allGenres = await res.json();
    
    // Fill catalog filter dropdown
    catalogGenreFilter.innerHTML = '<option value="">All Genres</option>';
    allGenres.forEach(genre => {
      const opt = document.createElement('option');
      opt.value = genre;
      opt.textContent = genre;
      catalogGenreFilter.appendChild(opt);
    });
  } catch (e) {
    console.error("Error loading genres list:", e);
  }
}

function renderWizardGenres() {
  wizardGenreSelector.innerHTML = '';
  allGenres.forEach(genre => {
    const tag = document.createElement('span');
    tag.className = `genre-tag ${wizardSelectedGenres.includes(genre) ? 'selected' : ''}`;
    tag.textContent = genre;
    tag.addEventListener('click', () => {
      if (wizardSelectedGenres.includes(genre)) {
        wizardSelectedGenres = wizardSelectedGenres.filter(g => g !== genre);
        tag.classList.remove('selected');
      } else {
        wizardSelectedGenres.push(genre);
        tag.classList.add('selected');
      }
    });
    wizardGenreSelector.appendChild(tag);
  });
}

async function fetchWizardRecommendations() {
  wizardResultsContainer.style.display = 'block';
  wizardLoader.style.display = 'flex';
  wizardGrid.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE}/api/recommend/by-preferences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        genres: wizardSelectedGenres,
        keywords: wizardKeywords.value,
        min_rating: parseFloat(wizardRatingSlider.value),
        limit: 12
      })
    });
    
    const data = await response.json();
    const recommendations: Book[] = data.recommendations || [];
    wizardGrid.innerHTML = '';

    if (recommendations.length === 0) {
      wizardGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 2rem 0;">We couldn\'t find matches. Try adjusting filters or typing simpler keywords!</div>';
      wizardGrid.style.display = 'block';
    } else {
      recommendations.forEach(book => {
        wizardGrid.appendChild(createBookCard(book));
      });
      wizardGrid.style.display = 'grid';
    }
  } catch (e) {
    console.error("Error generating recommendations:", e);
    wizardGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--accent-pink); padding: 2rem 0;">Error fetching recommendations. Please retry.</div>';
    wizardGrid.style.display = 'block';
  } finally {
    wizardLoader.style.display = 'none';
  }
}

// Logic: Details Modal
async function openDetailsModal(book: Book) {
  bookModal.style.display = 'flex';
  
  // Set modal details
  modalCoverContainer.innerHTML = book.image_url 
    ? `<img src="${book.image_url}" alt="${book.title}" id="modal-cover-img">`
    : createFallbackCoverHTML(book.title, book.authors);
  
  if (book.image_url) {
    const img = modalCoverContainer.querySelector('img') as HTMLImageElement;
    img.addEventListener('error', () => {
      modalCoverContainer.innerHTML = createFallbackCoverHTML(book.title, book.authors);
    });
  }

  modalTitle.textContent = book.title;
  modalAuthors.textContent = `by ${parseList(book.authors).join(', ')}`;
  
  modalTags.innerHTML = '';
  parseList(book.genres).forEach(g => {
    const tagSpan = document.createElement('span');
    tagSpan.className = 'detail-tag';
    tagSpan.textContent = g;
    modalTags.appendChild(tagSpan);
  });

  const ratingSpan = modalRating.querySelector('span') as HTMLSpanElement;
  ratingSpan.textContent = book.average_rating.toFixed(2);
  modalRatingsCount.textContent = book.ratings_count.toLocaleString();
  modalPages.textContent = book.pages ? book.pages.toString() : 'N/A';
  modalPublished.textContent = book.publish_date || 'N/A';
  modalDescription.textContent = book.description || 'No synopsis available for this book.';

  // Load Similar Books
  similarLoader.style.display = 'flex';
  similarGrid.style.display = 'none';
  similarGrid.innerHTML = '';

  try {
    const res = await fetch(`${API_BASE}/api/recommend/by-book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: book.book_id, limit: 5 })
    });
    const data = await res.json();
    const recommendations: Book[] = data.recommendations || [];

    if (recommendations.length === 0) {
      similarGrid.innerHTML = '<p style="color: var(--text-secondary);">No similar books found.</p>';
      similarGrid.style.display = 'block';
    } else {
      recommendations.forEach(simBook => {
        similarGrid.appendChild(createBookCard(simBook, true));
      });
      similarGrid.style.display = 'grid';
    }
  } catch (e) {
    console.error("Error loading similar books:", e);
    similarGrid.innerHTML = '<p style="color: var(--accent-pink);">Error loading recommendations.</p>';
    similarGrid.style.display = 'block';
  } finally {
    similarLoader.style.display = 'none';
  }
}

function closeDetailsModal() {
  bookModal.style.display = 'none';
}

// Debounce helper for instant searches without API abuse
function debounce(func: Function, wait: number) {
  let timeout: number | null = null;
  return function (...args: any[]) {
    const later = () => {
      timeout = null;
      func.apply(null, args);
    };
    if (timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait) as any;
  };
}

// Event Listeners Configuration
function initEventListeners() {
  logoHome.addEventListener('click', () => {
    currentPage = 1;
    searchQuery = '';
    selectedGenre = '';
    catalogSearch.value = '';
    catalogGenreFilter.value = '';
    switchTab('explore');
  });

  tabExplore.addEventListener('click', () => switchTab('explore'));
  tabWizard.addEventListener('click', () => switchTab('wizard'));

  // Debounced live typing search
  catalogSearch.addEventListener('input', debounce((e: Event) => {
    searchQuery = (e.target as HTMLInputElement).value;
    currentPage = 1;
    fetchCatalog();
  }, 300));

  catalogGenreFilter.addEventListener('change', (e) => {
    selectedGenre = (e.target as HTMLSelectElement).value;
    currentPage = 1;
    fetchCatalog();
  });

  paginationPrev.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      fetchCatalog();
    }
  });

  paginationNext.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage++;
      fetchCatalog();
    }
  });

  // Slider change display
  wizardRatingSlider.addEventListener('input', (e) => {
    wizardRatingVal.textContent = parseFloat((e.target as HTMLInputElement).value).toFixed(1);
  });

  wizardSubmitBtn.addEventListener('click', () => {
    fetchWizardRecommendations();
  });

  // Modal events
  modalCloseBtn.addEventListener('click', closeDetailsModal);
  bookModal.addEventListener('click', (e) => {
    if (e.target === bookModal) {
      closeDetailsModal();
    }
  });
  
  // Close modal on Escape key press
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDetailsModal();
    }
  });
}

// App Initialization
async function init() {
  initEventListeners();
  // Fetch initial genres dropdown and initial book catalog list
  await fetchGenres();
  await fetchCatalog();
}

window.addEventListener('DOMContentLoaded', init);
