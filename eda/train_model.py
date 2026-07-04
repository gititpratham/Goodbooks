#!/usr/bin/env python3
"""
=========================================================
  GOODBOOKS-10K — HYBRID ML RECOMMENDATION MODEL
  Training Script  (Full-data version)
=========================================================
Trains a Neural Ranker on ALL 53,424 users from ratings.csv.

Architecture — Pairwise MLP:
  Content-Based : TF-IDF + SVD descriptions (64d)
                  Genre multi-hot  (39d)
                  Mood  multi-hot  ( 8d)
                  Numeric features ( 4d)  — pages, year, rating, popularity
  Collaborative : Training signal from ratings.csv
                  user_pref_vec = mean feature vector of 4–5★ rated books
  Model Input   : concat(user_pref[115d], book_feat[115d]) = 230d
  MLP Layers    : 230 → 256 → 128 → 64 → 1  (ReLU + Adam + early stopping)

Run from goodbooks/eda/:
  pip install scikit-learn pandas numpy joblib
  python train_model.py

Saves to ./model/:
  recommender_full.joblib   ← the trained model (also copied as recommender_best.joblib)
=========================================================
"""

import os, ast, time, warnings, joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, roc_auc_score,
    precision_score, recall_score,
)

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── Paths ─────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.join(BASE, "..")
ARCH       = os.path.join(BASE, "archive")

ENRICHED_PATH = os.path.join(ROOT, "backend", "data", "books_enriched.csv")
RATINGS_PATH  = os.path.join(ARCH, "ratings.csv")
MODEL_DIR     = os.path.join(BASE, "model")
os.makedirs(MODEL_DIR, exist_ok=True)

# ─── Hyper-parameters ──────────────────────────────────────────────
MAX_POS_USER = 5       # max positive examples per user
MAX_NEG_USER = 5       # max negative examples per user
N_SVD_DIMS   = 64      # description embedding dimensions
TEST_FRAC    = 0.15    # held-out test fraction

# ─── Mood taxonomy ─────────────────────────────────────────────────
MOOD_LIST = [
    "Cozy", "Dark & Twisty", "Fast-Paced", "Slow Burn",
    "Thought-Provoking", "Escapist", "Heartwarming", "Unsettling",
]
MOOD_KEYWORDS = {
    "Cozy"             : ["cozy","comfort","warm","gentle","heartwarming","light"],
    "Dark & Twisty"    : ["dark","grim","disturbing","bleak","noir","dystopian"],
    "Fast-Paced"       : ["thriller","suspense","fast","action","gripping"],
    "Slow Burn"        : ["literary","contemplative","meditative","quiet","introspective"],
    "Thought-Provoking": ["philosophical","existential","cerebral","intellectual","profound"],
    "Escapist"         : ["fantasy","magic","adventure","world-building","epic","quest"],
    "Heartwarming"     : ["heartwarming","feel-good","uplifting","inspiring","redemption"],
    "Unsettling"       : ["horror","creepy","unsettling","eerie","psychological","disturbing"],
}

def parse_list(val):
    if pd.isna(val): return []
    try:    return [x.strip().lower() for x in ast.literal_eval(str(val))]
    except: return []

def tag_moods(desc):
    if not isinstance(desc, str): return []
    d = desc.lower()
    return [m for m, kws in MOOD_KEYWORDS.items() if any(k in d for k in kws)]

def sep(ch="═"): print(ch * 60, flush=True)
def log(msg=""):  print(msg, flush=True)


# ══════════════════════════════════════════════════════════════════
#  1. LOAD DATA
# ══════════════════════════════════════════════════════════════════
sep()
log("  GOODBOOKS HYBRID ML RECOMMENDER — TRAINING (FULL DATA)")
sep()
log()
log("[1/5] Loading data ...")

enriched = pd.read_csv(ENRICHED_PATH)
ratings  = pd.read_csv(RATINGS_PATH)

log(f"  books_enriched : {len(enriched):,} books × {enriched.shape[1]} cols")
log(f"  ratings.csv    : {len(ratings):,} ratings | "
    f"{ratings['user_id'].nunique():,} users | "
    f"{ratings['book_id'].nunique():,} books")

# Clean & derive
enriched = enriched.drop_duplicates(subset=["book_id"])
enriched["genres_list"] = enriched["genres"].apply(parse_list)
enriched["mood_tags"]   = enriched["description"].apply(tag_moods)
enriched["pub_year"]    = pd.to_numeric(enriched["original_publication_year"], errors="coerce")
enriched["pages"]       = pd.to_numeric(enriched["pages"], errors="coerce")

# Sort so row index is stable
enriched  = enriched.sort_values("book_id").reset_index(drop=True)
BOOK_IDS  = enriched["book_id"].tolist()
BID2ROW   = {bid: i for i, bid in enumerate(BOOK_IDS)}
N_BOOKS   = len(BOOK_IDS)
log(f"  Unique genres  : {enriched['genres_list'].explode().nunique()}")


# ══════════════════════════════════════════════════════════════════
#  2. FEATURE ENGINEERING  (115-dim vector per book)
# ══════════════════════════════════════════════════════════════════
log()
log("[2/5] Engineering book features ...")

# ── Genre multi-hot (39d) ──────────────────────────────────────────
GENRE_LIST   = sorted(set(g for gl in enriched["genres_list"] for g in gl if g))
GENRE_TO_IDX = {g: i for i, g in enumerate(GENRE_LIST)}

genre_mat = np.zeros((N_BOOKS, len(GENRE_LIST)), dtype=np.float32)
for i, gl in enumerate(enriched["genres_list"]):
    for g in gl:
        if g in GENRE_TO_IDX:
            genre_mat[i, GENRE_TO_IDX[g]] = 1.0

# ── Mood multi-hot (8d) ────────────────────────────────────────────
MOOD_TO_IDX = {m: i for i, m in enumerate(MOOD_LIST)}
mood_mat = np.zeros((N_BOOKS, len(MOOD_LIST)), dtype=np.float32)
for i, ml in enumerate(enriched["mood_tags"]):
    for m in ml:
        if m in MOOD_TO_IDX:
            mood_mat[i, MOOD_TO_IDX[m]] = 1.0

# ── Numeric (4d): pages, pub_year, avg_rating, log_ratings ─────────
PAGES_MED = enriched["pages"].median()
YEAR_MED  = enriched["pub_year"].median()

num_df = pd.DataFrame({
    "pages"       : enriched["pages"].fillna(PAGES_MED),
    "pub_year"    : enriched["pub_year"].fillna(YEAR_MED),
    "avg_rating"  : enriched["average_rating"].fillna(4.0),
    "log_ratings" : np.log1p(enriched["ratings_count"].fillna(0)),
})
scaler  = MinMaxScaler()
num_mat = scaler.fit_transform(num_df).astype(np.float32)

# ── Description TF-IDF → TruncatedSVD (64d) ───────────────────────
log("  Building TF-IDF + SVD description embeddings ...")
descs      = enriched["description"].fillna("").tolist()
tfidf      = TfidfVectorizer(max_features=12000, stop_words="english",
                             ngram_range=(1, 2), min_df=3, max_df=0.85)
desc_tfidf = tfidf.fit_transform(descs)
svd        = TruncatedSVD(n_components=N_SVD_DIMS, random_state=42)
desc_svd   = svd.fit_transform(desc_tfidf).astype(np.float32)
log(f"  SVD explained variance: {svd.explained_variance_ratio_.sum():.2%}")

# ── Stack → 39 + 8 + 4 + 64 = 115 dims ───────────────────────────
BOOK_FEATS = np.hstack([genre_mat, mood_mat, num_mat, desc_svd])
FEAT_DIM   = BOOK_FEATS.shape[1]
log(f"  Book feature matrix: {BOOK_FEATS.shape}  ({FEAT_DIM} dims per book)")


# ══════════════════════════════════════════════════════════════════
#  3. BUILD TRAINING DATA  (all 53,424 users)
# ══════════════════════════════════════════════════════════════════
log()
log("[3/5] Building training data from ALL users ...")

t0 = time.time()
X_list, y_list = [], []
skipped = 0
total   = ratings["user_id"].nunique()
log(f"  Total users: {total:,}")

for idx, (uid, grp) in enumerate(ratings.groupby("user_id")):
    if idx % 5000 == 0 and idx > 0:
        elapsed = time.time() - t0
        log(f"  {idx:>6,}/{total:,} users | {len(X_list):,} examples | {elapsed:.0f}s elapsed")

    liked_bids    = grp[grp["rating"] >= 4]["book_id"].values
    disliked_bids = grp[grp["rating"] <= 2]["book_id"].values

    liked_rows    = [BID2ROW[b] for b in liked_bids    if b in BID2ROW]
    disliked_rows = [BID2ROW[b] for b in disliked_bids if b in BID2ROW]

    if len(liked_rows) < 2:
        skipped += 1
        continue

    # User taste profile = centroid of liked book features
    user_pref = BOOK_FEATS[liked_rows].mean(axis=0)

    # Positive examples
    for row_i in liked_rows[:MAX_POS_USER]:
        X_list.append(np.concatenate([user_pref, BOOK_FEATS[row_i]]))
        y_list.append(1)

    # Negative examples: disliked books + random unrated
    neg_rows = list(disliked_rows[: MAX_NEG_USER // 2])
    n_random = MAX_NEG_USER - len(neg_rows)
    if n_random > 0:
        rated_set = {BID2ROW[b] for b in grp["book_id"].values if b in BID2ROW}
        pool      = [i for i in range(N_BOOKS) if i not in rated_set]
        if pool:
            neg_rows.extend(
                np.random.choice(pool, min(n_random, len(pool)), replace=False).tolist()
            )
    for row_i in neg_rows[:MAX_NEG_USER]:
        X_list.append(np.concatenate([user_pref, BOOK_FEATS[row_i]]))
        y_list.append(0)

X = np.array(X_list, dtype=np.float32)
y = np.array(y_list,  dtype=np.int32)
elapsed = time.time() - t0
log(f"  Done in {elapsed:.1f}s | {len(X):,} examples | "
    f"{y.sum():,} positive ({y.mean()*100:.1f}%) | "
    f"{skipped:,} users skipped (too few liked books)")


# ══════════════════════════════════════════════════════════════════
#  4. TRAIN MLP
# ══════════════════════════════════════════════════════════════════
log()
log("[4/5] Training MLP ...")

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=TEST_FRAC, random_state=42, stratify=y
)
log(f"  Train: {len(X_tr):,}  |  Test: {len(X_te):,}  |  Input dim: {X_tr.shape[1]}")

mlp = MLPClassifier(
    hidden_layer_sizes=(256, 128, 64),
    activation="relu",
    solver="adam",
    alpha=1e-4,
    batch_size=1024,
    learning_rate="adaptive",
    learning_rate_init=1e-3,
    max_iter=100,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=8,
    tol=1e-4,
    random_state=42,
    verbose=True,
)

t0 = time.time()
mlp.fit(X_tr, y_tr)
elapsed = time.time() - t0
log(f"  Training done in {elapsed:.1f}s | {mlp.n_iter_} iterations")


# ══════════════════════════════════════════════════════════════════
#  5. EVALUATE, SAVE & SMOKE TEST
# ══════════════════════════════════════════════════════════════════
log()
log("[5/5] Evaluating ...")

y_pred  = mlp.predict(X_te)
y_proba = mlp.predict_proba(X_te)[:, 1]
auc     = roc_auc_score(y_te, y_proba)
prec    = precision_score(y_te, y_pred, zero_division=0)
rec     = recall_score(y_te, y_pred, zero_division=0)

log(classification_report(y_te, y_pred, target_names=["Disliked", "Liked"]))
log(f"  ROC-AUC   : {auc:.4f}")
log(f"  Precision : {prec:.4f}  |  Recall : {rec:.4f}")

# Save
meta_cols = ["book_id","title","authors","average_rating","genres",
             "description","pages","pub_year","image_url","ratings_count"]
meta_df = enriched[meta_cols].copy().set_index("book_id")

bundle = dict(
    mlp          = mlp,
    tfidf        = tfidf,
    svd          = svd,
    scaler       = scaler,
    book_features= BOOK_FEATS,
    book_ids     = BOOK_IDS,
    genre_list   = GENRE_LIST,
    genre_to_idx = GENRE_TO_IDX,
    mood_list    = MOOD_LIST,
    mood_to_idx  = MOOD_TO_IDX,
    mood_keywords= MOOD_KEYWORDS,
    pages_median = float(PAGES_MED),
    year_median  = float(YEAR_MED),
    meta         = meta_df,
    auc          = auc,
    n_train      = len(X),
    model_label  = "FULL",
)

for fname in ["recommender_full.joblib", "recommender_best.joblib"]:
    path = os.path.join(MODEL_DIR, fname)
    joblib.dump(bundle, path, compress=3)
    log(f"  Saved: {os.path.getsize(path)/1e6:.1f} MB → {path}")

# Smoke test
log()
log("  Smoke test → Fantasy + Escapist + Heartwarming, ≥4.0★, ≤500pp ...")

test_genres = ["fantasy"]; test_moods = ["Escapist","Heartwarming"]
min_rat = 4.0; max_pgs = 500

gv = np.zeros(len(GENRE_LIST), dtype=np.float32)
for g in test_genres:
    if g in GENRE_TO_IDX: gv[GENRE_TO_IDX[g]] = 1.0
mv = np.zeros(len(MOOD_LIST), dtype=np.float32)
for m in test_moods:
    if m in MOOD_TO_IDX: mv[MOOD_TO_IDX[m]] = 1.0
num_raw  = np.array([[max_pgs, 2005.0, min_rat, np.log1p(50000)]], dtype=np.float32)
nv       = scaler.transform(num_raw).flatten()
pseudo   = " ".join(test_genres + test_moods + ["magic","adventure","heartwarming"])
dv       = svd.transform(tfidf.transform([pseudo])).flatten().astype(np.float32)
upref    = np.concatenate([gv, mv, nv, dv])
scores   = mlp.predict_proba(np.hstack([np.tile(upref,(N_BOOKS,1)), BOOK_FEATS]))[:,1]

hits = []
for i,(bid,sc) in enumerate(zip(BOOK_IDS, scores)):
    if bid not in meta_df.index: continue
    bk = meta_df.loc[bid]
    if bk["average_rating"] < min_rat: continue
    pgs = bk.get("pages")
    if max_pgs and pgs and not pd.isna(pgs) and pgs > max_pgs: continue
    hits.append((sc, str(bk["title"]), float(bk["average_rating"]),
                 int(pgs) if pgs and not pd.isna(pgs) else 0))
hits.sort(reverse=True)

log(f"  {'Score':>7}  {'★':>4}  {'pp':>5}  Title")
log("  " + "─"*65)
for sc,title,rat,pgs in hits[:10]:
    log(f"  {sc:.4f}  {rat:.2f}  {pgs:>5}  {title[:50]}")

sep()
log("  TRAINING COMPLETE")
log(f"  AUC={auc:.4f} | Acc={((y_pred==y_te).sum()/len(y_te))*100:.1f}% | "
    f"Training pairs={len(X):,} | Users={total:,}")
log(f"  Model saved → {MODEL_DIR}/")
sep()
