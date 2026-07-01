import logging
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BookRecommender:
    def __init__(self):
        self.books = []
        self.book_id_to_idx = {}
        self.vectorizer = TfidfVectorizer(stop_words='english', min_df=2)
        self.tfidf_matrix = None
        self.popular_books_fallback = []

    def clean_text(self, text):
        """Cleans and normalizes text fields, replacing None/NaN with empty strings."""
        if not text or pd.isna(text):
            return ""
        # Clean formatting like string representations of lists if needed
        # but for simple TF-IDF we can just strip quotes and brackets
        text = str(text).replace('[', '').replace(']', '').replace("'", "").replace('"', '').replace(',', ' ')
        return text.lower()

    def fit(self, books_list):
        """
        Fits the TF-IDF vectorizer on the database book metadata.
        This runs once during server startup.
        """
        if not books_list:
            logger.warning("Recommender received an empty books list. Fitting skipped.")
            return

        self.books = books_list
        logger.info(f"Fitting recommendation model on {len(self.books)} books...")
        
        # Build mapping for quick index lookup
        self.book_id_to_idx = {book["book_id"]: idx for idx, book in enumerate(self.books)}
        
        # Build fallback list (top books sorted by rating count and average rating)
        sorted_by_popularity = sorted(
            self.books,
            key=lambda x: (x.get("ratings_count") or 0, x.get("average_rating") or 0.0),
            reverse=True
        )
        self.popular_books_fallback = sorted_by_popularity[:50]

        # Combine text fields for content-based matching
        combined_features = []
        for book in self.books:
            title = self.clean_text(book.get("title"))
            authors = self.clean_text(book.get("authors"))
            genres = self.clean_text(book.get("genres"))
            description = self.clean_text(book.get("description"))
            
            # Weighted combination of fields: repeat title, authors, and genres to give them higher importance
            feature_str = f"{title} {title} {authors} {authors} {genres} {genres} {description}"
            combined_features.append(feature_str)

        # Fit TF-IDF Vectorizer
        self.tfidf_matrix = self.vectorizer.fit_transform(combined_features)
        logger.info("TF-IDF vectorizer fit completed successfully.")

    def get_popular_fallback(self, limit=10):
        """Returns the most popular/highly rated books as a fallback."""
        # Add random perturbation or just return top slice
        return self.popular_books_fallback[:limit]

    def get_recommendations_by_book(self, book_id: int, limit: int = 10):
        """
        Finds books similar to the given book ID.
        Uses cosine similarity of precalculated TF-IDF vectors.
        """
        if self.tfidf_matrix is None or book_id not in self.book_id_to_idx:
            logger.warning(f"Book ID {book_id} not found in recommender index. Returning popular fallback.")
            return self.get_popular_fallback(limit)

        idx = self.book_id_to_idx[book_id]
        
        # Compute cosine similarity between the selected book and all others
        # linear_kernel is equivalent to cosine_similarity when TF-IDF vectors are L2-normalized
        cosine_sim = linear_kernel(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        
        # Get indices of books sorted by similarity score (descending)
        similar_indices = np.argsort(cosine_sim)[::-1]
        
        # Filter out the requested book itself and collect top matches
        recommendations = []
        for i in similar_indices:
            rec_book = self.books[i]
            if rec_book["book_id"] == book_id:
                continue
            recommendations.append(rec_book)
            if len(recommendations) >= limit:
                break
                
        return recommendations

    def get_recommendations_by_preferences(self, genres: list = None, keywords: str = "", min_rating: float = 0.0, limit: int = 10):
        """
        Finds books matching custom user preferences.
        Creates a query vector and calculates cosine similarity.
        """
        if self.tfidf_matrix is None:
            return self.get_popular_fallback(limit)

        genres = genres or []
        genres_str = " ".join([self.clean_text(g) for g in genres])
        keywords_str = self.clean_text(keywords)
        
        # Combine user selections into a single search query profile
        query_profile = f"{genres_str} {genres_str} {keywords_str}"
        
        if not query_profile.strip():
            # If query is completely empty, return popular books
            return self.get_popular_fallback(limit)

        # Vectorize the query profile
        query_vector = self.vectorizer.transform([query_profile])
        
        # Calculate cosine similarity with all books
        cosine_sim = linear_kernel(query_vector, self.tfidf_matrix).flatten()
        
        # Get sorted indices
        similar_indices = np.argsort(cosine_sim)[::-1]
        
        recommendations = []
        for idx in similar_indices:
            book = self.books[idx]
            
            # Apply hard filters (e.g., minimum rating)
            if book.get("average_rating", 0.0) < min_rating:
                continue
                
            recommendations.append(book)
            if len(recommendations) >= limit:
                break
                
        # If filters were too strict and we have fewer recommendations than requested, fill with popular books
        if len(recommendations) < limit:
            fallback = self.get_popular_fallback(limit * 2)
            for f_book in fallback:
                if f_book["book_id"] not in [r["book_id"] for r in recommendations]:
                    recommendations.append(f_book)
                if len(recommendations) >= limit:
                    break

        return recommendations
