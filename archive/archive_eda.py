"""
=========================================================
  GOODBOOKS-10K ARCHIVE — MULTI-FILE EDA
  Files: books.csv · ratings.csv · book_tags.csv
         tags.csv · to_read.csv · sample_book.xml
=========================================================
Run from the eda/ folder:
    python archive_eda.py

Outputs: ./eda_output/archive/ — 14 PNG plots + console report
"""

import os, warnings, xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from collections import Counter

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ARCH_DIR   = os.path.join(BASE_DIR, "archive")
OUT_DIR    = os.path.join(BASE_DIR, "eda_output", "archive")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Brand palette ──────────────────────────────────────────────────
C_INK    = "#111111"
C_PAPER  = "#EDEAE0"
C_RED    = "#FF3D2E"
C_BLUE   = "#2F5EFF"
C_YELLOW = "#FFD400"
PAL = [C_RED, C_BLUE, C_YELLOW, "#6A0DAD", "#00897B",
       "#F4511E", "#3949AB", "#00ACC1", "#E91E63", "#43A047"]

plt.rcParams.update({
    "figure.facecolor": C_PAPER, "axes.facecolor": C_PAPER,
    "axes.edgecolor": C_INK, "axes.labelcolor": C_INK,
    "xtick.color": C_INK, "ytick.color": C_INK,
    "text.color": C_INK, "font.family": "monospace",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#CCCCCC", "grid.linewidth": 0.5,
    "savefig.facecolor": C_PAPER, "savefig.dpi": 150,
})

def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  [saved] {name}")


# ══════════════════════════════════════════════════════════════════
#  LOAD ALL FILES
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ARCHIVE EDA — Loading all files")
print("="*60)

books     = pd.read_csv(os.path.join(ARCH_DIR, "books.csv"))
ratings   = pd.read_csv(os.path.join(ARCH_DIR, "ratings.csv"))
book_tags = pd.read_csv(os.path.join(ARCH_DIR, "book_tags.csv"))
tags      = pd.read_csv(os.path.join(ARCH_DIR, "tags.csv"))
to_read   = pd.read_csv(os.path.join(ARCH_DIR, "to_read.csv"))

for name, df in [("books", books), ("ratings", ratings),
                 ("book_tags", book_tags), ("tags", tags), ("to_read", to_read)]:
    print(f"  {name:12s}: {df.shape[0]:>8,} rows × {df.shape[1]} cols | "
          f"{df.isnull().sum().sum()} nulls")

# ── Derived on books ───────────────────────────────────────────────
books["pub_year"] = pd.to_numeric(books["original_publication_year"], errors="coerce")
books["log_rc"]   = np.log1p(books["ratings_count"])
books["pct_5star"] = books["ratings_5"] / books["ratings_count"].replace(0, np.nan)
books["pct_1star"] = books["ratings_1"] / books["ratings_count"].replace(0, np.nan)

# ── Merge tags ─────────────────────────────────────────────────────
bt_tagged = book_tags.merge(tags, on="tag_id", how="left")

print("\n  Files loaded. Starting plots...\n")


# ══════════════════════════════════════════════════════════════════
#  PLOT A1 — Multi-file Dataset Overview
# ══════════════════════════════════════════════════════════════════
print("[A01/14] Multi-file overview")

files_info = {
    "books.csv":     (len(books), books.shape[1], books.isnull().sum().sum()),
    "ratings.csv":   (len(ratings), ratings.shape[1], 0),
    "book_tags.csv": (len(book_tags), book_tags.shape[1], 0),
    "tags.csv":      (len(tags), tags.shape[1], 0),
    "to_read.csv":   (len(to_read), to_read.shape[1], 0),
}

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("A01 · Archive Dataset — File Overview", fontsize=15, fontweight="bold")

# File size bar chart (rows)
ax = axes[0]
f_names  = list(files_info.keys())
f_rows   = [v[0] for v in files_info.values()]
bars = ax.bar(f_names, f_rows, color=[PAL[i] for i in range(len(f_names))],
              edgecolor=C_INK, linewidth=1.2)
ax.set_title("Row Count per File")
ax.set_ylabel("# Rows")
ax.tick_params(axis="x", rotation=20)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
for b, v in zip(bars, f_rows):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+500,
            f"{v:,}", ha="center", fontsize=9, fontweight="bold")

# Summary table
ax2 = axes[1]
ax2.axis("off")
rows_tbl = [
    ["File", "Rows", "Cols", "Nulls"],
    *[[fn, f"{v[0]:,}", str(v[1]), str(v[2])] for fn, v in files_info.items()],
    ["──────", "──────", "──", "──"],
    ["Unique Users (ratings)", f"{ratings['user_id'].nunique():,}", "─", "─"],
    ["Unique Users (to_read)", f"{to_read['user_id'].nunique():,}", "─", "─"],
    ["Unique Tags", f"{tags['tag_id'].nunique():,}", "─", "─"],
    ["Tag assignments", f"{len(book_tags):,}", "─", "─"],
]
tbl = ax2.table(cellText=rows_tbl[1:], colLabels=rows_tbl[0],
                cellLoc="left", loc="center", bbox=[0, 0, 1, 1])
tbl.auto_set_font_size(False); tbl.set_fontsize(10)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor(C_INK)
    cell.set_facecolor(C_YELLOW if r == 0 else C_PAPER)
    cell.set_text_props(weight="bold" if r == 0 else "normal")

savefig("A01_overview.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A2 — books.csv — Rating Distribution
# ══════════════════════════════════════════════════════════════════
print("[A02/14] books.csv — Rating distribution")

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
fig.suptitle("A02 · books.csv — Rating Distribution  ◀ MIN RATING slider ▶",
             fontsize=13, fontweight="bold")

ax = axes[0]
ax.hist(books["average_rating"].dropna(), bins=50,
        color=C_RED, edgecolor=C_INK, linewidth=0.7)
ax.axvline(books["average_rating"].mean(), color=C_BLUE, lw=2, ls="--",
           label=f"Mean {books['average_rating'].mean():.2f}")
ax.axvline(books["average_rating"].median(), color=C_YELLOW, lw=2, ls="--",
           label=f"Median {books['average_rating'].median():.2f}")
ax.set_title("Avg Rating Distribution (books.csv)")
ax.set_xlabel("Average Rating"); ax.set_ylabel("# Books")
ax.legend()

# Ratings count log
ax = axes[1]
ax.hist(books["log_rc"].dropna(), bins=50, color=C_BLUE, edgecolor=C_INK, linewidth=0.7)
ax.set_title("log(Ratings Count) Distribution")
ax.set_xlabel("log(1 + ratings_count)"); ax.set_ylabel("# Books")

# Scatter ratings_count vs avg_rating
ax = axes[2]
sample_b = books.sample(min(3000, len(books)), random_state=1)
ax.scatter(sample_b["ratings_count"], sample_b["average_rating"],
           alpha=0.35, s=10, c=C_RED, edgecolors="none")
ax.set_xscale("log")
ax.set_title("Popularity vs. Rating")
ax.set_xlabel("Ratings Count (log)"); ax.set_ylabel("Average Rating")

savefig("A02_books_ratings.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A3 — books.csv — Star Breakdown
# ══════════════════════════════════════════════════════════════════
print("[A03/14] books.csv — Star rating breakdown")

star_cols  = ["ratings_1","ratings_2","ratings_3","ratings_4","ratings_5"]
star_totals = books[star_cols].sum()

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
fig.suptitle("A03 · books.csv — Star Rating Analysis", fontsize=13, fontweight="bold")

# Pie of total star distribution
ax = axes[0]
star_colors = [C_RED, "#FF8C00", C_YELLOW, "#66BB6A", C_BLUE]
wedges, texts, autotexts = ax.pie(
    star_totals.values, labels=["1★","2★","3★","4★","5★"],
    colors=star_colors, autopct="%1.1f%%",
    pctdistance=0.75, startangle=90,
    wedgeprops=dict(edgecolor=C_INK, linewidth=1.5))
for at in autotexts: at.set_fontsize(9); at.set_color(C_INK)
ax.set_title("Overall Star Distribution (all 10k books)")

# Top 10 by 5★ count
ax = axes[1]
top5 = books.nlargest(10, "ratings_5")[["title","ratings_5"]].copy()
top5["title"] = top5["title"].str[:22] + "…"
bars_5 = ax.barh(top5["title"][::-1], top5["ratings_5"][::-1],
                 color=C_BLUE, edgecolor=C_INK, linewidth=1)
ax.set_title("Top 10 — Most 5★ Ratings")
ax.set_xlabel("5★ Count")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x/1e6)}M" if x>=1e6 else f"{int(x/1e3)}k"))

# % 5star vs avg_rating
ax = axes[2]
s5 = books.dropna(subset=["pct_5star","average_rating"])
ax.scatter(s5["pct_5star"], s5["average_rating"],
           alpha=0.3, s=8, c=C_YELLOW, edgecolors=C_INK, linewidths=0.3)
ax.set_title("% 5★ Reviews vs. Avg Rating")
ax.set_xlabel("Fraction of 5★ Reviews"); ax.set_ylabel("Average Rating")

savefig("A03_star_breakdown.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A4 — books.csv — Publication Year
# ══════════════════════════════════════════════════════════════════
print("[A04/14] books.csv — Publication year  ◀ YEAR slider ▶")

year_clean = books[books["pub_year"].between(1850, 2017)]
decade_cnt = year_clean.copy()
decade_cnt["decade"] = (decade_cnt["pub_year"] // 10 * 10).astype(int)
d_cnt = decade_cnt.groupby("decade").size()
d_rat = decade_cnt.groupby("decade")["average_rating"].mean()

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
fig.suptitle("A04 · books.csv — Publication Year  ◀ RECENT ↔ OLD slider ▶",
             fontsize=13, fontweight="bold")

ax = axes[0]
ax.hist(year_clean["pub_year"], bins=60, color=C_RED, edgecolor=C_INK, linewidth=0.5)
ax.set_title("Publication Year Distribution")
ax.set_xlabel("Year"); ax.set_ylabel("# Books")

ax = axes[1]
ax.bar(d_cnt.index, d_cnt.values, width=8, color=C_BLUE, edgecolor=C_INK, linewidth=0.7)
ax.set_title("Books per Decade")
ax.set_xlabel("Decade"); ax.set_ylabel("# Books")

ax = axes[2]
ax.plot(d_rat.index, d_rat.values, color=C_RED, lw=2, marker="o", ms=5)
ax.axhline(books["average_rating"].mean(), color=C_YELLOW, lw=1.5, ls="--", label="Overall mean")
ax.set_title("Avg Rating by Decade")
ax.set_xlabel("Decade"); ax.set_ylabel("Average Rating")
ax.legend()

savefig("A04_pub_year.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A5 — books.csv — Language & Author
# ══════════════════════════════════════════════════════════════════
print("[A05/14] books.csv — Language & author analysis")

top_lang    = books["language_code"].value_counts().head(12)
top_authors = books["authors"].value_counts().head(15)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("A05 · books.csv — Language & Author", fontsize=13, fontweight="bold")

ax = axes[0]
ax.bar(top_lang.index, top_lang.values,
       color=[PAL[i % len(PAL)] for i in range(len(top_lang))],
       edgecolor=C_INK, linewidth=1)
ax.set_title("Books by Language Code")
ax.set_xlabel("Language Code"); ax.set_ylabel("# Books")
ax.tick_params(axis="x", rotation=25)
for i, (lbl, val) in enumerate(top_lang.items()):
    ax.text(i, val+30, f"{val:,}", ha="center", fontsize=8)

ax2 = axes[1]
ax2.barh(top_authors.index[::-1], top_authors.values[::-1],
         color=[PAL[i % len(PAL)] for i in range(len(top_authors))][::-1],
         edgecolor=C_INK, linewidth=1)
ax2.set_title("Top 15 Most Represented Authors")
ax2.set_xlabel("# Books in Catalog")

savefig("A05_language_authors.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A6 — books.csv — Missing Values Heatmap
# ══════════════════════════════════════════════════════════════════
print("[A06/14] books.csv — Missing values")

null_df = books.isnull().sum()
null_df = null_df[null_df > 0].sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(10, 5))
fig.suptitle("A06 · books.csv — Missing Values per Column", fontsize=13, fontweight="bold")
bars_n = ax.barh(null_df.index, null_df.values, color=C_RED, edgecolor=C_INK, linewidth=1)
ax.set_xlabel("# Null Rows")
for b, v in zip(bars_n, null_df.values):
    pct = v / len(books) * 100
    ax.text(v+5, b.get_y()+b.get_height()/2, f"{v} ({pct:.1f}%)", va="center", fontsize=9)

savefig("A06_missing.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A7 — ratings.csv — Distribution & User Behaviour
# ══════════════════════════════════════════════════════════════════
print("[A07/14] ratings.csv — Rating distribution & user behaviour")

user_rc   = ratings.groupby("user_id")["rating"].count()
user_mean = ratings.groupby("user_id")["rating"].mean()
book_rc   = ratings.groupby("book_id")["rating"].count()
book_mean = ratings.groupby("book_id")["rating"].mean()

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("A07 · ratings.csv — Distribution & User Behaviour", fontsize=13, fontweight="bold")

# Overall rating value dist
ax = axes[0][0]
rc_dist = ratings["rating"].value_counts().sort_index()
bars_r = ax.bar(rc_dist.index, rc_dist.values,
                color=star_colors, edgecolor=C_INK, linewidth=1.2, width=0.6)
ax.set_title("Distribution of Explicit Ratings\n(981k user-book ratings)")
ax.set_xlabel("Rating (1–5★)"); ax.set_ylabel("# Ratings")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x/1e3)}k"))
for b, v in zip(bars_r, rc_dist.values):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+500,
            f"{v/1e3:.0f}k", ha="center", fontsize=9)

# Ratings per user histogram
ax = axes[0][1]
ax.hist(np.log1p(user_rc), bins=60, color=C_BLUE, edgecolor=C_INK, linewidth=0.5)
ax.axvline(np.log1p(user_rc.mean()), color=C_RED, lw=2, ls="--",
           label=f"Mean {user_rc.mean():.1f} ratings/user")
ax.set_title("Ratings per User (log scale)")
ax.set_xlabel("log(1 + # Ratings)"); ax.set_ylabel("# Users")
ax.legend(fontsize=9)

# Ratings per book histogram
ax = axes[1][0]
ax.hist(np.log1p(book_rc), bins=60, color=C_YELLOW, edgecolor=C_INK, linewidth=0.5)
ax.axvline(np.log1p(book_rc.mean()), color=C_RED, lw=2, ls="--",
           label=f"Mean {book_rc.mean():.1f} ratings/book")
ax.set_title("Ratings per Book (log scale)")
ax.set_xlabel("log(1 + # Ratings)"); ax.set_ylabel("# Books rated")
ax.legend(fontsize=9)

# User mean rating distribution
ax = axes[1][1]
ax.hist(user_mean, bins=50, color=C_RED, edgecolor=C_INK, linewidth=0.5)
ax.axvline(user_mean.mean(), color=C_BLUE, lw=2, ls="--",
           label=f"Mean {user_mean.mean():.2f}")
ax.set_title("Mean Rating given per User\n(rating bias distribution)")
ax.set_xlabel("User Mean Rating"); ax.set_ylabel("# Users")
ax.legend()

savefig("A07_ratings_distribution.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A8 — ratings.csv — Book-level aggregates
# ══════════════════════════════════════════════════════════════════
print("[A08/14] ratings.csv — Book-level aggregates")

book_agg = ratings.groupby("book_id").agg(
    n_ratings=("rating","count"),
    mean_rating=("rating","mean"),
    std_rating=("rating","std"),
).reset_index()

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
fig.suptitle("A08 · ratings.csv — Book-level Aggregates", fontsize=13, fontweight="bold")

ax = axes[0]
ax.scatter(book_agg["n_ratings"], book_agg["mean_rating"],
           alpha=0.3, s=6, c=C_BLUE, edgecolors="none")
ax.set_xscale("log")
ax.set_title("# Ratings vs. Mean Rating per Book")
ax.set_xlabel("# Ratings (log)"); ax.set_ylabel("Mean Rating")

ax = axes[1]
ax.hist(book_agg["mean_rating"].dropna(), bins=50,
        color=C_RED, edgecolor=C_INK, linewidth=0.7)
ax.axvline(book_agg["mean_rating"].mean(), color=C_YELLOW, lw=2, ls="--",
           label=f"Mean {book_agg['mean_rating'].mean():.2f}")
ax.set_title("Book Mean Rating (from explicit ratings)")
ax.set_xlabel("Mean Rating"); ax.set_ylabel("# Books")
ax.legend()

ax = axes[2]
ax.hist(book_agg["std_rating"].dropna(), bins=50,
        color=C_YELLOW, edgecolor=C_INK, linewidth=0.7)
ax.set_title("Rating Std Dev per Book\n(measures polarisation)")
ax.set_xlabel("Std Dev of Ratings"); ax.set_ylabel("# Books")

savefig("A08_book_aggregates.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A9 — tags.csv + book_tags.csv — Tag Analysis
# ══════════════════════════════════════════════════════════════════
print("[A09/14] tags.csv + book_tags.csv — Tag frequency  ◀ GENRE/MOOD ▶")

# Top tags by total count across all books
top_tags_count = (bt_tagged.groupby("tag_name")["count"].sum()
                  .sort_values(ascending=False).head(30))

# Top tags by number of books they appear on
top_tags_books = (bt_tagged.groupby("tag_name")["goodreads_book_id"].nunique()
                  .sort_values(ascending=False).head(30))

fig, axes = plt.subplots(1, 2, figsize=(17, 8))
fig.suptitle("A09 · book_tags + tags — Top Tags  ◀ GENRE & MOOD signals ▶",
             fontsize=13, fontweight="bold")

ax = axes[0]
t30 = top_tags_count.head(20)
ax.barh(t30.index[::-1], t30.values[::-1],
        color=[PAL[i % len(PAL)] for i in range(20)][::-1],
        edgecolor=C_INK, linewidth=1)
ax.set_title("Top 20 Tags by Total Tag Count")
ax.set_xlabel("Cumulative tag count across all books")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x/1e6)}M" if x>=1e6 else f"{int(x/1e3)}k"))

ax2 = axes[1]
b30 = top_tags_books.head(20)
ax2.barh(b30.index[::-1], b30.values[::-1],
         color=[PAL[i % len(PAL)] for i in range(20)][::-1],
         edgecolor=C_INK, linewidth=1)
ax2.set_title("Top 20 Tags by # Books They Appear On")
ax2.set_xlabel("# Unique Books Tagged")
for b, v in zip(ax2.patches, b30.values[::-1]):
    ax2.text(v+10, b.get_y()+b.get_height()/2, f"{v:,}", va="center", fontsize=8)

savefig("A09_tags.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A10 — Mood/Genre tags (filtered useful subset)
# ══════════════════════════════════════════════════════════════════
print("[A10/14] Mood/Genre tag deep-dive")

# Genre-like tags: pick tags that are clearly genre/mood words
GENRE_KWS = ["fiction","fantasy","mystery","romance","horror","science-fiction",
              "thriller","historical","non-fiction","literary","classic","adventure",
              "young-adult","biography","self-help","dystopian","magical-realism",
              "graphic-novel","poetry","children","crime","paranormal","comic"]
MOOD_KWS  = ["dark","cozy","funny","humorous","heartwarming","inspiring","thought-provoking",
              "fast-paced","slow","emotional","feel-good","atmospheric","psychological"]

def match_any(tag, kws):
    t = str(tag).lower()
    return any(k in t for k in kws)

tag_summary = bt_tagged.groupby("tag_name").agg(
    total_count=("count","sum"),
    book_count=("goodreads_book_id","nunique")
).reset_index()

genre_tags = tag_summary[tag_summary["tag_name"].apply(lambda x: match_any(x, GENRE_KWS))]\
    .nlargest(20, "total_count")
mood_tags = tag_summary[tag_summary["tag_name"].apply(lambda x: match_any(x, MOOD_KWS))]\
    .nlargest(20, "total_count")

fig, axes = plt.subplots(1, 2, figsize=(17, 7))
fig.suptitle("A10 · Curated Genre & Mood Tags from book_tags  ◀ FORM FIELDS ▶",
             fontsize=13, fontweight="bold")

ax = axes[0]
ax.barh(genre_tags["tag_name"][::-1], genre_tags["total_count"][::-1],
        color=C_BLUE, edgecolor=C_INK, linewidth=1)
ax.set_title("Genre-like Tags (total count)")
ax.set_xlabel("Cumulative Count")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x/1e6)}M" if x>=1e6 else f"{int(x/1e3)}k"))

ax2 = axes[1]
ax2.barh(mood_tags["tag_name"][::-1], mood_tags["total_count"][::-1],
         color=C_RED, edgecolor=C_INK, linewidth=1)
ax2.set_title("Mood-like Tags (total count)")
ax2.set_xlabel("Cumulative Count")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x/1e6)}M" if x>=1e6 else f"{int(x/1e3)}k"))

savefig("A10_genre_mood_tags.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A11 — to_read.csv — Wishlist Behaviour
# ══════════════════════════════════════════════════════════════════
print("[A11/14] to_read.csv — Wishlist behaviour")

wishlist_per_user = to_read.groupby("user_id")["book_id"].count()
wishlist_per_book = to_read.groupby("book_id")["user_id"].count()
top_wishlisted    = wishlist_per_book.sort_values(ascending=False).head(15)
# Map book IDs to titles
id_to_title = books.set_index("id")["title"].to_dict()
top_wishlisted.index = [str(id_to_title.get(bid, f"BookID {bid}"))[:25]+"…"
                        for bid in top_wishlisted.index]

fig, axes = plt.subplots(1, 3, figsize=(17, 6))
fig.suptitle("A11 · to_read.csv — Wishlist (Want-to-Read) Analysis",
             fontsize=13, fontweight="bold")

ax = axes[0]
ax.hist(np.log1p(wishlist_per_user), bins=60, color=C_BLUE, edgecolor=C_INK, linewidth=0.5)
ax.axvline(np.log1p(wishlist_per_user.mean()), color=C_RED, lw=2, ls="--",
           label=f"Mean {wishlist_per_user.mean():.1f}/user")
ax.set_title("Wishlist Size per User (log)")
ax.set_xlabel("log(1 + # Books on Wishlist)"); ax.set_ylabel("# Users")
ax.legend(fontsize=9)

ax = axes[1]
ax.hist(np.log1p(wishlist_per_book), bins=60, color=C_YELLOW, edgecolor=C_INK, linewidth=0.5)
ax.axvline(np.log1p(wishlist_per_book.mean()), color=C_RED, lw=2, ls="--",
           label=f"Mean {wishlist_per_book.mean():.1f}/book")
ax.set_title("Times a Book is Wishlisted (log)")
ax.set_xlabel("log(1 + # Users who want it)"); ax.set_ylabel("# Books")
ax.legend(fontsize=9)

ax2 = axes[2]
bars_w = ax2.barh(top_wishlisted.index[::-1], top_wishlisted.values[::-1],
                  color=C_RED, edgecolor=C_INK, linewidth=1)
ax2.set_title("Top 15 Most Wishlisted Books")
ax2.set_xlabel("# Users who want to read it")
for b, v in zip(bars_w, top_wishlisted.values[::-1]):
    ax2.text(v+20, b.get_y()+b.get_height()/2, f"{v:,}", va="center", fontsize=8)

savefig("A11_to_read.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A12 — Cross-file: Wishlist vs Ratings vs Avg Rating
# ══════════════════════════════════════════════════════════════════
print("[A12/14] Cross-file — Wishlist vs. Ratings vs. Quality")

wishlist_count = to_read.groupby("book_id")["user_id"].count().rename("wishlist_count")
ratings_count2 = ratings.groupby("book_id")["rating"].count().rename("n_ratings")
book_cross = books.set_index("id")[["average_rating","ratings_count"]].join(wishlist_count).join(ratings_count2)
book_cross = book_cross.dropna()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("A12 · Cross-file — Wishlist vs. Engagement",
             fontsize=13, fontweight="bold")

ax = axes[0]
ax.scatter(np.log1p(book_cross["ratings_count"]), np.log1p(book_cross["wishlist_count"]),
           alpha=0.3, s=8, c=C_BLUE, edgecolors="none")
ax.set_title("log(Ratings Count) vs. log(Wishlist Count)")
ax.set_xlabel("log(Ratings Count)"); ax.set_ylabel("log(Wishlist Count)")

ax2 = axes[1]
ax2.scatter(book_cross["average_rating"], np.log1p(book_cross["wishlist_count"]),
            alpha=0.3, s=8, c=C_RED, edgecolors="none")
ax2.set_title("Avg Rating vs. log(Wishlist Count)")
ax2.set_xlabel("Average Rating"); ax2.set_ylabel("log(Wishlist Count)")

savefig("A12_cross_wishlist.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A13 — Correlation Heatmap (books.csv numerics)
# ══════════════════════════════════════════════════════════════════
print("[A13/14] Correlation heatmap — books.csv")

num_cols = ["average_rating","ratings_count","work_ratings_count",
            "work_text_reviews_count","ratings_1","ratings_2",
            "ratings_3","ratings_4","ratings_5","pub_year","books_count"]
corr = books[num_cols].corr()

fig, ax = plt.subplots(figsize=(11, 9))
fig.suptitle("A13 · books.csv — Numeric Feature Correlation", fontsize=13, fontweight="bold")
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(len(num_cols))); ax.set_xticklabels(num_cols, rotation=45, ha="right")
ax.set_yticks(range(len(num_cols))); ax.set_yticklabels(num_cols)
plt.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
for i in range(len(num_cols)):
    for j in range(len(num_cols)):
        v = corr.values[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                color="white" if abs(v) > 0.5 else C_INK)

savefig("A13_correlation.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT A14 — sample_book.xml — Structure snapshot
# ══════════════════════════════════════════════════════════════════
print("[A14/14] sample_book.xml — Field inventory")

xml_path = os.path.join(ARCH_DIR, "sample_book.xml")
tree = ET.parse(xml_path)
root = tree.getroot()

fields, values = [], []
for child in root:
    tag = child.tag.strip()
    val = (child.text or "").strip()[:60]
    fields.append(tag)
    values.append(val if val else "(empty/nested)")

fig, ax = plt.subplots(figsize=(12, max(6, len(fields)*0.35)))
fig.suptitle("A14 · sample_book.xml — Field Inventory (Goodreads API structure)",
             fontsize=13, fontweight="bold")
ax.axis("off")
tbl_data = [[f, v] for f, v in zip(fields, values)]
tbl = ax.table(cellText=tbl_data, colLabels=["XML Field", "Sample Value"],
               cellLoc="left", loc="center", bbox=[0, 0, 1, 1])
tbl.auto_set_font_size(False); tbl.set_fontsize(9)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor(C_INK)
    if r == 0:
        cell.set_facecolor(C_YELLOW)
        cell.set_text_props(weight="bold")
    else:
        cell.set_facecolor(C_PAPER if r % 2 == 0 else "#F5F2E8")

savefig("A14_xml_fields.png")


# ══════════════════════════════════════════════════════════════════
#  CONSOLE SUMMARY
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ARCHIVE EDA COMPLETE — SUMMARY")
print("="*60)
print(f"""
FILE SUMMARY
  books.csv     : {len(books):,} books × {books.shape[1]} cols  |  2,975 nulls (isbn, lang, etc.)
  ratings.csv   : {len(ratings):,} explicit ratings  |  {ratings['user_id'].nunique():,} users, {ratings['book_id'].nunique():,} books
  book_tags.csv : {len(book_tags):,} tag assignments  |  {book_tags['goodreads_book_id'].nunique():,} books tagged
  tags.csv      : {len(tags):,} unique tags
  to_read.csv   : {len(to_read):,} wishlist entries  |  {to_read['user_id'].nunique():,} users

KEY STATS (books.csv)
  Avg Rating    : Mean {books['average_rating'].mean():.3f}  |  Std {books['average_rating'].std():.3f}
  Ratings Count : Mean {books['ratings_count'].mean():,.0f}  |  Max {books['ratings_count'].max():,}
  Pub Year      : {int(books['pub_year'].dropna().min())} – {int(books['pub_year'].dropna().max())}

KEY STATS (ratings.csv)
  Total ratings   : {len(ratings):,}
  Ratings/user    : Mean {len(ratings)/ratings['user_id'].nunique():.1f}
  Ratings/book    : Mean {len(ratings)/ratings['book_id'].nunique():.1f}
  Rating values   : {dict(ratings['rating'].value_counts().sort_index())}

KEY STATS (to_read.csv)
  Wishlist/user   : Mean {len(to_read)/to_read['user_id'].nunique():.1f}
  Wishlist/book   : Mean {len(to_read)/to_read['book_id'].nunique():.1f}

KEY STATS (book_tags.csv)
  Avg tags/book   : {len(book_tags)/book_tags['goodreads_book_id'].nunique():.1f}
  Most popular tag: {bt_tagged.groupby('tag_name')['count'].sum().idxmax()}

FORM FIELD → ARCHIVE FILE MAPPING
  [GENRE multi-select]     → book_tags.csv + tags.csv  (filter by tag_name)
  [MOOD multi-select]      → book_tags.csv  (dark, cozy, etc. tag_names)
  [MIN RATING slider]      → books.csv: average_rating  (range 2.47–4.82)
  [LIGHT ↔ HEAVY slider]  → NOT in books.csv  (use books_enriched.csv pages)
  [RECENT ↔ OLD slider]   → books.csv: original_publication_year
  [Popularity weight]      → ratings.csv: n_ratings OR to_read.csv wishlist count
  [Author preference]      → books.csv: authors column

MODEL TRAINING SIGNALS FROM ARCHIVE
  ✓ ratings.csv     → explicit collaborative filtering (user-item matrix)
  ✓ to_read.csv     → implicit feedback signal (strong positive signal)
  ✓ book_tags.csv   → user-crowdsourced genre/mood tags (richer than enriched)
  ✓ books.csv       → metadata features (rating, year, language)
  ✗ books.csv       → no 'pages' column (use books_enriched.csv for that)
  ✗ ratings.csv     → no timestamps (can't model reading recency)

RECOMMENDED ARCHITECTURE
  Content-Based  : books_enriched.csv (genres, description, pages)
  Collaborative  : ratings.csv (explicit) + to_read.csv (implicit)
  Tag-Based      : book_tags.csv (crowdsourced genre/mood labelling)
  Hybrid         : combine all three with weighted scoring
""")

print(f"  All 14 plots saved to: {OUT_DIR}/")
print("="*60)
