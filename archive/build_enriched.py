import sqlite3
import pandas as pd

DB_PATH = "/Users/suvidhaair/Downloads/JTP/goodbooks/backend/goodbooks_dump.db"
OUT_CSV = "/Users/suvidhaair/Downloads/JTP/goodbooks/backend/db/books_enriched.csv"

GENRE_TAG_MAP = {
    "Fantasy":          ["fantasy", "high-fantasy", "epic-fantasy", "fantasy-fiction", "urban-fantasy", "dark-fantasy", "sword-and-sorcery"],
    "Sci-Fi":           ["science-fiction", "sci-fi", "scifi", "space-opera", "hard-science-fiction", "dystopia", "cyberpunk"],
    "Mystery":          ["mystery", "cozy-mystery", "detective", "whodunit", "mystery-thriller", "british-mysteries"],
    "Romance":          ["romance", "contemporary-romance", "historical-romance", "romantic", "love-story", "romance-novels"],
    "Literary Fiction": ["literary-fiction", "literary", "contemporary-fiction", "classics", "general-fiction", "contemporary", "fiction"],
    "Horror":           ["horror", "horror-fiction", "supernatural", "gothic", "paranormal-horror", "ghost-stories"],
    "Non-Fiction":      ["non-fiction", "nonfiction", "self-help", "biography", "memoir", "history", "true-crime", "popular-science"],
    "Thriller":         ["thriller", "suspense", "psychological-thriller", "crime-thriller", "crime", "political-thriller"],
    "Historical":       ["historical-fiction", "historical", "historical-romance", "historical-mystery", "medieval"],
    "Young Adult":      ["young-adult", "ya", "ya-fiction", "teen", "young-adult-fiction", "ya-fantasy"],
    "Graphic Novel":    ["graphic-novel", "comics", "manga", "graphic-novels", "comic-book", "sequential-art"],
}

_GENRE_DISPLAY = {
    "fantasy": "Fantasy", "science-fiction": "Sci-Fi", "sci-fi": "Sci-Fi",
    "mystery": "Mystery", "romance": "Romance", "literary-fiction": "Literary",
    "literary": "Literary", "horror": "Horror", "non-fiction": "Non-Fiction",
    "nonfiction": "Non-Fiction", "thriller": "Thriller", "suspense": "Thriller",
    "historical-fiction": "Historical", "historical": "Historical",
    "young-adult": "YA", "contemporary": "Contemporary", "classics": "Classics",
    "biography": "Biography", "memoir": "Memoir", "self-help": "Self-Help",
    "crime": "Crime", "dystopia": "Dystopian", "paranormal": "Paranormal",
    "fiction": "Fiction", "general-fiction": "Fiction", "graphic-novel": "Graphic Novel",
}

def build_enriched():
    conn = sqlite3.connect(DB_PATH)
    books_df = pd.read_sql("SELECT id as book_id, title, authors, average_rating, ratings_count, pub_year as original_publication_year, image_url, description FROM books", conn)
    books_df["pages"] = None
    
    tags_df = pd.read_sql("SELECT tag_id, tag_name FROM tags", conn)
    tag_id_to_name = dict(zip(tags_df['tag_id'], tags_df['tag_name']))

    book_tags_df = pd.read_sql("SELECT book_id, tag_id, count FROM book_tags WHERE count > 20", conn)
    
    tag_name_to_genre = {}
    for genre, tag_names in GENRE_TAG_MAP.items():
        for t in tag_names:
            tag_name_to_genre[t] = _GENRE_DISPLAY.get(t, genre)
    
    book_genres = {}
    for _, row in book_tags_df.iterrows():
        bid = row['book_id']
        tid = row['tag_id']
        tname = tag_id_to_name.get(tid)
        if tname and tname in tag_name_to_genre:
            g = tag_name_to_genre[tname]
            if bid not in book_genres:
                book_genres[bid] = []
            if g not in book_genres[bid]:
                book_genres[bid].append(g)
    
    books_df['genres'] = books_df['book_id'].map(lambda x: str(book_genres.get(x, [])))
    books_df.to_csv(OUT_CSV, index=False)
    print("Saved", OUT_CSV)

if __name__ == "__main__":
    build_enriched()
