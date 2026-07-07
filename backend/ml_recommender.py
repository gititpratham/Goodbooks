"""
=========================================================
  GOODBOOKS ML RECOMMENDER — Inference Module
=========================================================
Usage:
  from ml_recommender import MLBookRecommender

  rec = MLBookRecommender("model/recommender.joblib")

  books = rec.recommend(
      genres    = ["fantasy", "mystery"],
      moods     = ["Cozy", "Escapist"],
      min_rating = 4.0,
      max_pages  = 400,
      year_pref  = "any",   # "recent" | "any" | "classic"
      n          = 10,
  )

  for b in books:
      print(b["title"], b["ml_score"], b["average_rating"])
=========================================================
"""

import os
import logging
import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)


class MLBookRecommender:
    """
    Hybrid ML book recommender (Neural Ranker + Content-Based + Filters).

    Model: MLPClassifier trained on pairwise (user_pref_vec, book_feat_vec) → P(liked).
    Features: genre multi-hot · mood multi-hot · numeric (pages, year, rating, popularity)
              · TF-IDF + TruncatedSVD description embedding.
    """

    # Year ranges for filter modes
    YEAR_RANGE = {
        "recent" : (2000, 2030),
        "any"    : (0,    2030),
        "classic": (0,    1980),
    }
    # Ideal year used when building the user preference vector
    IDEAL_YEAR = {
        "recent" : 2012.0,
        "any"    : 1995.0,
        "classic": 1960.0,
    }

    # ─────────────────────────────────────────────────────────────
    def __init__(self, model_path: str):
        """Load the pre-trained model bundle from disk."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at '{model_path}'. Run train_model.py first."
            )
        logger.info(f"Loading model from {model_path} ...")
        bundle = joblib.load(model_path)

        self.mlp          = bundle["mlp"]
        self.tfidf        = bundle["tfidf"]
        self.svd          = bundle["svd"]
        self.scaler       = bundle["scaler"]
        self.book_feats   = bundle["book_features"]      # (N, 115)
        self.book_ids     = bundle["book_ids"]           # list of sequential IDs
        self.genre_list   = bundle["genre_list"]
        self.genre_to_idx = bundle["genre_to_idx"]
        self.mood_list    = bundle["mood_list"]
        self.mood_to_idx  = bundle["mood_to_idx"]
        self.mood_kws     = bundle["mood_keywords"]
        self.meta         = bundle["meta"]               # DataFrame indexed by book_id
        self.pages_median = float(bundle.get("pages_median", 336.0))
        self.year_median  = float(bundle.get("year_median",  2004.0))
        self.model_auc    = bundle.get("auc")
        self.model_label  = bundle.get("model_label", "?")
        self.n_books      = len(self.book_ids)

        auc_str = f"{self.model_auc:.4f}" if self.model_auc else "N/A"
        logger.info(
            f"Loaded {self.model_label} model | "
            f"{self.n_books:,} books | AUC = {auc_str}"
        )

    # ─────────────────────────────────────────────────────────────
    def _build_pref_vector(
        self,
        genres: list,
        moods: list,
        min_rating: float,
        max_pages: int | None,
        year_pref: str,
    ) -> np.ndarray:
        """
        Convert form inputs into a 115-dim preference vector matching the
        book feature space so the MLP can score them pairwise.

        Layout mirrors BOOK_FEATS:
          [0:39]    → genre multi-hot
          [39:47]   → mood multi-hot
          [47:51]   → numeric (pages, year, avg_rating, log_ratings)
          [51:115]  → desc SVD embedding (pseudo-text from genres+moods)
        """
        # Genre multi-hot
        gv = np.zeros(len(self.genre_list), dtype=np.float32)
        for g in genres:
            k = g.lower().strip()
            if k in self.genre_to_idx:
                gv[self.genre_to_idx[k]] = 1.0

        # Mood multi-hot
        mv = np.zeros(len(self.mood_list), dtype=np.float32)
        for m in moods:
            if m in self.mood_to_idx:
                mv[self.mood_to_idx[m]] = 1.0

        # Numeric — express user's "ideal book" in the same feature space
        ideal_pages = float(max_pages) if max_pages else self.pages_median
        ideal_year  = self.IDEAL_YEAR.get(year_pref, self.year_median)
        ideal_pop   = np.log1p(30_000.0)   # medium popularity (neutral prior)

        num_raw = np.array(
            [[ideal_pages, ideal_year, float(min_rating), ideal_pop]],
            dtype=np.float32,
        )
        nv = self.scaler.transform(num_raw).flatten()

        # Pseudo-description embedding: genres + moods + their keywords
        pseudo_words = list(genres) + list(moods)
        for m in moods:
            pseudo_words.extend(self.mood_kws.get(m, []))
        pseudo = " ".join(pseudo_words) or "book fiction"
        dv = self.svd.transform(
            self.tfidf.transform([pseudo])
        ).flatten().astype(np.float32)

        return np.concatenate([gv, mv, nv, dv])   # 39+8+4+64 = 115 dims

    # ─────────────────────────────────────────────────────────────
    def recommend(
        self,
        genres: list       = None,
        moods: list        = None,
        min_rating: float  = 3.0,
        max_pages: int     = None,
        year_pref: str     = "any",
        popularity_pref: str = "popular",
        n: int             = 10,
    ) -> list[dict]:
        """
        Return the top-N books that best match the user's preferences.

        Args:
            genres     : List of genre strings, e.g. ["fantasy", "mystery"]
            moods      : List of mood strings, e.g. ["Cozy", "Escapist"]
            min_rating : Minimum acceptable average rating  (0.0 – 5.0)
            max_pages  : Maximum page count; None = no upper limit
            year_pref  : "recent" (≥2000) | "any" (no filter) | "classic" (<1980)
            popularity_pref: "popular" or "underrated"
            n          : Number of books to return

        Returns:
            List of dicts sorted by ml_score descending. Each dict contains:
            book_id, title, authors, average_rating, genres, description,
            pages, pub_year, image_url, ratings_count, ml_score.
        """
        genres = [g for g in (genres or []) if g]
        moods  = [m for m in (moods  or []) if m]

        # 1. Build 115-dim user preference vector from form inputs
        user_pref = self._build_pref_vector(genres, moods, min_rating, max_pages, year_pref)

        # 2. Pairwise MLP scoring:
        #    input = concat(user_pref[115], book_feat[115]) = 230 dims per pair
        user_tiled = np.tile(user_pref, (self.n_books, 1))   # (N, 115)
        X_inf      = np.hstack([user_tiled, self.book_feats]) # (N, 230)
        scores     = self.mlp.predict_proba(X_inf)[:, 1]      # P(liked) for each book

        # 3. Collect results with hard filters
        year_lo, year_hi = self.YEAR_RANGE.get(year_pref, (0, 2030))
        results = []

        for i, (bid, sc) in enumerate(zip(self.book_ids, scores)):
            if bid not in self.meta.index:
                continue

            bk    = self.meta.loc[bid]
            avg_r = float(bk.get("average_rating") or 0)
            pages = bk.get("pages")
            pyear = bk.get("pub_year")
            ratings_count = int(bk.get("ratings_count") or 0)

            # Hard filter: minimum rating
            if avg_r < min_rating:
                continue
            # Hard filter: max pages
            if max_pages and pages is not None and not pd.isna(pages) and pages > max_pages:
                continue
            # Hard filter: publication year range
            if pyear is not None and not pd.isna(pyear):
                if not (year_lo <= int(pyear) <= year_hi):
                    continue
            # Hard filter: Popularity (underrated drops books with > 65000 ratings)
            if popularity_pref == "underrated" and ratings_count > 65000:
                continue

            results.append({
                "book_id"       : int(bid),
                "title"         : str(bk.get("title", "")),
                "authors"       : str(bk.get("authors", "")),
                "average_rating": round(avg_r, 2),
                "genres"        : str(bk.get("genres", "[]")),
                "description"   : str(bk.get("description", ""))[:400],
                "pages"         : int(pages) if pages is not None and not pd.isna(pages) else None,
                "pub_year"      : int(pyear) if pyear is not None and not pd.isna(pyear) else None,
                "image_url"     : str(bk.get("image_url", "")),
                "ratings_count" : ratings_count,
                "ml_score"      : round(float(sc), 4),
            })

        # 4. Sort by ML score and return top-N
        results.sort(key=lambda x: x["ml_score"], reverse=True)
        return results[:n]

    # ─────────────────────────────────────────────────────────────
    def explain(
        self,
        book_id: int,
        genres: list,
        moods: list,
    ) -> dict:
        """
        Return a human-readable breakdown of WHY a book was recommended.

        Args:
            book_id : Sequential book ID (1–10000)
            genres  : Genres the user selected
            moods   : Moods the user selected

        Returns:
            Dict with matched_genres, matched_moods, book metadata.
        """
        bid_to_row = {bid: i for i, bid in enumerate(self.book_ids)}
        if book_id not in bid_to_row:
            return {"error": f"book_id {book_id} not in index"}

        row_i   = bid_to_row[book_id]
        bk_feat = self.book_feats[row_i]
        n_g     = len(self.genre_list)
        n_m     = len(self.mood_list)

        # Genre overlap
        user_gv  = np.zeros(n_g, dtype=np.float32)
        for g in genres:
            k = g.lower().strip()
            if k in self.genre_to_idx: user_gv[self.genre_to_idx[k]] = 1.0
        book_gv      = bk_feat[:n_g]
        genre_matches = [self.genre_list[j] for j in range(n_g)
                         if user_gv[j] > 0 and book_gv[j] > 0]

        # Mood overlap
        user_mv  = np.zeros(n_m, dtype=np.float32)
        for m in moods:
            if m in self.mood_to_idx: user_mv[self.mood_to_idx[m]] = 1.0
        book_mv      = bk_feat[n_g: n_g + n_m]
        mood_matches  = [self.mood_list[j] for j in range(n_m)
                         if user_mv[j] > 0 and book_mv[j] > 0]

        bk = self.meta.loc[book_id] if book_id in self.meta.index else {}
        return {
            "book_id"       : book_id,
            "title"         : str(bk.get("title", "")),
            "matched_genres": genre_matches,
            "matched_moods" : mood_matches,
            "avg_rating"    : float(bk.get("average_rating", 0)),
            "pages"         : bk.get("pages"),
            "pub_year"      : bk.get("pub_year"),
            "genre_overlap" : len(genre_matches),
            "mood_overlap"  : len(mood_matches),
        }

    # ─────────────────────────────────────────────────────────────
    def model_info(self) -> dict:
        """Return metadata about the loaded model."""
        return {
            "model_label" : self.model_label,
            "roc_auc"     : round(self.model_auc, 4) if self.model_auc else None,
            "n_books"     : self.n_books,
            "n_genres"    : len(self.genre_list),
            "n_moods"     : len(self.mood_list),
            "genres"      : self.genre_list,
            "moods"       : self.mood_list,
        }


# ─── CLI demo ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    model_path = os.path.join(os.path.dirname(__file__), "model", "recommender.joblib")
    if len(sys.argv) > 1:
        model_path = sys.argv[1]

    print(f"\nLoading model: {model_path}")
    rec = MLBookRecommender(model_path)
    print(f"Model info: {rec.model_info()}\n")

    # Demo query
    results = rec.recommend(
        genres     = ["fantasy", "fiction"],
        moods      = ["Escapist", "Heartwarming"],
        min_rating = 4.0,
        max_pages  = 500,
        year_pref  = "any",
        n          = 10,
    )

    print(f"{'Rank':<5} {'Score':>7}  {'Rating':>6}  {'Pages':>5}  {'Year':>5}  Title")
    print("─" * 75)
    for rank, b in enumerate(results, 1):
        pgs  = str(b["pages"])  if b["pages"]  else "?"
        year = str(b["pub_year"]) if b["pub_year"] else "?"
        print(f"  #{rank:<3} {b['ml_score']:>7.4f}  {b['average_rating']:>6.2f}★  "
              f"{pgs:>5}pp  {year:>5}  {b['title'][:45]}")

    if results:
        print("\nExplain #1:")
        exp = rec.explain(results[0]["book_id"], ["fantasy","fiction"], ["Escapist","Heartwarming"])
        print(f"  Matched genres : {exp['matched_genres']}")
        print(f"  Matched moods  : {exp['matched_moods']}")
