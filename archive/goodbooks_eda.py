"""
========================================================
  GOODBOOKS-10K — EXPLORATORY DATA ANALYSIS
  For: GOOD/BOOKS Book Recommendation System
  Dataset: books_enriched.csv (goodbooks-10k on Kaggle)
========================================================
Run from the eda/ folder:
    pip install pandas matplotlib scikit-learn numpy
    python goodbooks_eda.py

Outputs: ./eda_output/ folder with 11 PNG plots + console report
"""

import os, ast, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from collections import Counter
from itertools import combinations

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "backend", "data", "books_enriched.csv")
OUT_DIR   = os.path.join(BASE_DIR, "eda_output")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Brand palette (matching GOOD/BOOKS frontend) ──────────────────
C_INK    = "#111111"
C_PAPER  = "#EDEAE0"
C_RED    = "#FF3D2E"
C_BLUE   = "#2F5EFF"
C_YELLOW = "#FFD400"
PAL = [C_RED, C_BLUE, C_YELLOW, "#6A0DAD", "#00897B",
       "#F4511E", "#3949AB", "#00ACC1", "#E91E63", "#43A047"]

# ── Global matplotlib style ────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor" : C_PAPER,
    "axes.facecolor"   : C_PAPER,
    "axes.edgecolor"   : C_INK,
    "axes.labelcolor"  : C_INK,
    "xtick.color"      : C_INK,
    "ytick.color"      : C_INK,
    "text.color"       : C_INK,
    "font.family"      : "monospace",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "axes.grid"        : True,
    "grid.color"       : "#CCCCCC",
    "grid.linewidth"   : 0.5,
    "savefig.facecolor": C_PAPER,
    "savefig.dpi"      : 150,
})

def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  [saved] {name}")


# ══════════════════════════════════════════════════════════════════
#  1. LOAD & CLEAN
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  GOODBOOKS-10K EDA")
print("="*60)

df = pd.read_csv(DATA_PATH)
print(f"  Loaded  : {df.shape[0]:,} rows × {df.shape[1]} cols")
df = df.drop_duplicates(subset=["book_id"])
print(f"  After dedup: {df.shape[0]:,} books")

# ── Parse list-string columns ──────────────────────────────────────
def parse_list_col(val):
    if pd.isna(val): return []
    try:    return [x.strip().lower() for x in ast.literal_eval(str(val))]
    except: return []

df["genres_list"]  = df["genres"].apply(parse_list_col)
df["authors_list"] = df["authors"].apply(parse_list_col)

# ── Numeric types ──────────────────────────────────────────────────
df["pub_year"]  = pd.to_numeric(df["original_publication_year"], errors="coerce")
df["pages"]     = pd.to_numeric(df["pages"], errors="coerce")

# ── Derived features ───────────────────────────────────────────────
# Page bucket  →  "light ↔ heavy" slider
def page_bucket(p):
    if pd.isna(p): return "Unknown"
    if p < 150:    return "< 150 (Flash)"
    if p < 300:    return "150-299 (Short)"
    if p < 500:    return "300-499 (Medium)"
    if p < 700:    return "500-699 (Long)"
    return                "700+ (Epic)"

PAGE_ORDER = ["< 150 (Flash)", "150-299 (Short)", "300-499 (Medium)",
              "500-699 (Long)", "700+ (Epic)", "Unknown"]
df["page_bucket"] = df["pages"].apply(page_bucket)

# Era bucket  →  "recent ↔ old" slider
def era_bucket(y):
    if pd.isna(y):  return "Unknown"
    if y >= 2010:   return "2010s+ (Recent)"
    if y >= 2000:   return "2000s"
    if y >= 1990:   return "1990s"
    if y >= 1980:   return "1980s"
    if y >= 1960:   return "1960-79"
    if y >= 1900:   return "1900-59"
    return                  "Pre-1900"

ERA_ORDER = ["Pre-1900","1900-59","1960-79","1980s","1990s","2000s","2010s+ (Recent)","Unknown"]
df["era"] = df["pub_year"].apply(era_bucket)

# Rating tier  →  min_rating slider
df["rating_tier"] = pd.cut(
    df["average_rating"],
    bins=[0, 3.5, 3.9, 4.2, 4.5, 5.1],
    labels=["<3.5", "3.5–3.9", "3.9–4.2", "4.2–4.5", "4.5+"]
)

# Log-popularity
df["log_ratings"] = np.log1p(df["ratings_count"])

# Mood tags from description (NLP keyword matching)
MOOD_MAP = {
    "Cozy"             : ["cozy","comfort","warm","gentle","heartwarming","light"],
    "Dark & Twisty"    : ["dark","grim","disturbing","bleak","noir","dystopian"],
    "Fast-Paced"       : ["thriller","suspense","fast","action","gripping"],
    "Slow Burn"        : ["literary","contemplative","meditative","quiet","introspective"],
    "Thought-Provoking": ["philosophical","existential","cerebral","intellectual","profound"],
    "Escapist"         : ["fantasy","magic","adventure","world-building","epic","quest"],
    "Heartwarming"     : ["heartwarming","feel-good","uplifting","inspiring","redemption"],
    "Unsettling"       : ["horror","creepy","unsettling","eerie","psychological","disturbing"],
}

def tag_moods(desc):
    if not isinstance(desc, str) or not desc.strip(): return []
    d = desc.lower()
    return [m for m, kws in MOOD_MAP.items() if any(k in d for k in kws)]

df["mood_tags"] = df["description"].apply(tag_moods)
df["mood_count"] = df["mood_tags"].str.len()


# ══════════════════════════════════════════════════════════════════
#  PLOT 01 — Dataset Overview
# ══════════════════════════════════════════════════════════════════
print("\n[01/11] Dataset Overview")

null_s = df.isnull().sum()
null_s = null_s[null_s > 0].sort_values()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("01 · Dataset Overview", fontsize=15, fontweight="bold")

# Missing values bar
ax = axes[0]
ax.barh(null_s.index, null_s.values, color=C_RED, edgecolor=C_INK, linewidth=1.2)
ax.set_title("Missing Values per Column")
ax.set_xlabel("# Null Rows")
for i, (idx, val) in enumerate(null_s.items()):
    ax.text(val + 2, i, str(val), va="center", fontsize=9)

# Summary table
ax2 = axes[1]
ax2.axis("off")
rows = [
    ["Total Books", f"{len(df):,}"],
    ["Unique Authors", f"{df['authors_list'].explode().nunique():,}"],
    ["Unique Genres", f"{df['genres_list'].explode().nunique():,}"],
    ["Mean Rating", f"{df['average_rating'].mean():.2f} ★"],
    ["Median Pages", f"{df['pages'].median():.0f} pp"],
    ["Pub Year Range", f"{int(df['pub_year'].dropna().min())} – {int(df['pub_year'].dropna().max())}"],
    ["Mean Ratings Count", f"{df['ratings_count'].mean():,.0f}"],
    ["Max Ratings Count", f"{df['ratings_count'].max():,}"],
    ["Missing Description", f"{df['description'].isna().sum()} books"],
    ["Missing Pages", f"{df['pages'].isna().sum()} books"],
]
tbl = ax2.table(cellText=rows, colLabels=["Metric", "Value"],
                cellLoc="left", loc="center", bbox=[0, 0, 1, 1])
tbl.auto_set_font_size(False); tbl.set_fontsize(11)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor(C_INK)
    cell.set_facecolor(C_YELLOW if r == 0 else C_PAPER)
    cell.set_text_props(weight="bold" if r == 0 else "normal")

savefig("01_overview.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 02 — Rating Distribution  (min_rating slider)
# ══════════════════════════════════════════════════════════════════
print("[02/11] Rating Distribution")

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("02 · Rating Distribution  ◀ MIN RATING slider ▶", fontsize=14, fontweight="bold")

# Histogram
ax = axes[0]
ax.hist(df["average_rating"].dropna(), bins=50, color=C_RED, edgecolor=C_INK, linewidth=0.7)
ax.axvline(df["average_rating"].mean(),   color=C_BLUE,   lw=2, ls="--",
           label=f"Mean  {df['average_rating'].mean():.2f}")
ax.axvline(df["average_rating"].median(), color=C_YELLOW, lw=2, ls="--",
           label=f"Median {df['average_rating'].median():.2f}")
ax.set_title("Distribution of Average Rating")
ax.set_xlabel("Average Rating"); ax.set_ylabel("# Books")
ax.legend()

# Rating tier bars
ax = axes[1]
tier_c = df["rating_tier"].value_counts().sort_index()
bars = ax.bar(tier_c.index, tier_c.values,
              color=[PAL[i] for i in range(len(tier_c))],
              edgecolor=C_INK, linewidth=1.2)
ax.set_title("Books per Rating Tier")
ax.set_xlabel("Tier"); ax.set_ylabel("# Books")
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+30,
            f"{int(b.get_height()):,}", ha="center", fontsize=9)

# Scatter popularity vs rating
ax = axes[2]
sample = df.sample(min(2000, len(df)), random_state=42)
ax.scatter(sample["ratings_count"], sample["average_rating"],
           alpha=0.35, s=8, c=C_BLUE, edgecolors="none")
ax.set_xscale("log")
ax.set_title("Popularity vs. Rating")
ax.set_xlabel("Ratings Count (log scale)"); ax.set_ylabel("Average Rating")

savefig("02_ratings.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 03 — Genre Frequency  (genre multi-select)
# ══════════════════════════════════════════════════════════════════
print("[03/11] Genre Frequency")

genre_ctr = Counter()
for gl in df["genres_list"]: genre_ctr.update(gl)
top20 = genre_ctr.most_common(20)
g_labels, g_counts = zip(*top20)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("03 · Genre Analysis  ◀ GENRE multi-select ▶", fontsize=14, fontweight="bold")

ax = axes[0]
ax.barh(g_labels[::-1], g_counts[::-1],
        color=[PAL[i % len(PAL)] for i in range(len(g_labels))][::-1],
        edgecolor=C_INK, linewidth=1)
ax.set_title("Top 20 Genres by Book Count")
ax.set_xlabel("# Books")
for i, (lbl, val) in enumerate(zip(g_labels[::-1], g_counts[::-1])):
    ax.text(val + 10, i, f"{val:,}", va="center", fontsize=8)

# Genre avg rating
ax2 = axes[1]
top15 = [g for g, _ in top20[:15]]
g_data = []
for g in top15:
    mask = df["genres_list"].apply(lambda x: g in x)
    g_data.append({"genre": g.title(), "mean_rating": df.loc[mask,"average_rating"].mean()})
gdf = pd.DataFrame(g_data).sort_values("mean_rating")
bars2 = ax2.barh(gdf["genre"], gdf["mean_rating"], color=C_YELLOW, edgecolor=C_INK, linewidth=1)
ax2.axvline(df["average_rating"].mean(), color=C_RED, lw=2, ls="--", label="Overall mean")
ax2.set_xlim(3.0, 4.6)
ax2.set_title("Avg Rating per Genre (Top 15)")
ax2.set_xlabel("Average Rating"); ax2.legend()
for b, v in zip(bars2, gdf["mean_rating"]):
    ax2.text(v+0.01, b.get_y()+b.get_height()/2, f"{v:.2f}", va="center", fontsize=9)

savefig("03_genres.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 04 — Genre Co-occurrence Matrix
# ══════════════════════════════════════════════════════════════════
print("[04/11] Genre Co-occurrence")

top10g = [g for g, _ in genre_ctr.most_common(10)]
cooc   = Counter()
for gl in df["genres_list"]:
    for a, b in combinations(sorted(set(gl)), 2):
        cooc[(a, b)] += 1

matrix = pd.DataFrame(0, index=top10g, columns=top10g)
for (a, b), cnt in cooc.items():
    if a in top10g and b in top10g:
        matrix.loc[a, b] += cnt
        matrix.loc[b, a] += cnt

fig, ax = plt.subplots(figsize=(10, 8))
fig.suptitle("04 · Genre Co-occurrence Matrix (Top 10 Genres)", fontsize=14, fontweight="bold")
im = ax.imshow(matrix.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(10)); ax.set_xticklabels([g.title() for g in top10g], rotation=45, ha="right")
ax.set_yticks(range(10)); ax.set_yticklabels([g.title() for g in top10g])
plt.colorbar(im, ax=ax, shrink=0.8, label="# Books sharing both genres")
for i in range(10):
    for j in range(10):
        v = matrix.values[i, j]
        if v > 0:
            ax.text(j, i, str(v), ha="center", va="center", fontsize=7,
                    color="white" if v > matrix.values.max()*0.5 else C_INK)

savefig("04_genre_cooccurrence.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 05 — Page Count / Reading Length  (length slider)
# ══════════════════════════════════════════════════════════════════
print("[05/11] Page Count / Reading Length")

page_clean = df["pages"].dropna()
page_clean = page_clean[page_clean.between(50, 1500)]

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("05 · Reading Length  ◀ LIGHT ↔ HEAVY slider ▶", fontsize=14, fontweight="bold")

ax = axes[0]
ax.hist(page_clean, bins=60, color=C_BLUE, edgecolor=C_INK, linewidth=0.5)
for pct, lbl in [(25,"Q1"),(50,"Median"),(75,"Q3")]:
    v = page_clean.quantile(pct/100)
    ax.axvline(v, lw=1.5, ls="--", color=C_RED, label=f"{lbl}: {v:.0f}")
ax.set_title("Distribution of Page Count (50–1500pp)")
ax.set_xlabel("Pages"); ax.set_ylabel("# Books")
ax.legend(fontsize=8)

ax = axes[1]
bucket_c = df["page_bucket"].value_counts().reindex(PAGE_ORDER, fill_value=0)
b_colors = [C_YELLOW, "#00ACC1", C_BLUE, C_RED, "#6A0DAD", "#AAAAAA"]
bars_b = ax.bar(bucket_c.index, bucket_c.values, color=b_colors,
                edgecolor=C_INK, linewidth=1.2)
ax.set_title("Books per Length Tier")
ax.set_xlabel("Page Bucket"); ax.set_ylabel("# Books")
ax.tick_params(axis="x", rotation=25)
for b in bars_b:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+15,
            f"{int(b.get_height()):,}", ha="center", fontsize=9)

ax = axes[2]
s3 = df[df["pages"].between(50,1500)].sample(min(2000,len(df)), random_state=7)
ax.scatter(s3["pages"], s3["average_rating"], alpha=0.3, s=8, c=C_RED, edgecolors="none")
ax.set_title("Page Count vs. Rating")
ax.set_xlabel("Pages"); ax.set_ylabel("Average Rating")

savefig("05_pages.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 06 — Publication Era  (year slider)
# ══════════════════════════════════════════════════════════════════
print("[06/11] Publication Era")

era_c = df["era"].value_counts().reindex(ERA_ORDER, fill_value=0)
decade_df = df[df["pub_year"].between(1900, 2020)].copy()
decade_df["pub_decade"] = (decade_df["pub_year"] // 10 * 10).astype(int)
dec_cnt = decade_df.groupby("pub_decade").size()
dec_rat = decade_df.groupby("pub_decade")["average_rating"].mean()

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
fig.suptitle("06 · Publication Era  ◀ RECENT ↔ OLD year slider ▶", fontsize=14, fontweight="bold")

ax = axes[0]
bars_e = ax.bar(era_c.index, era_c.values,
                color=[PAL[i % len(PAL)] for i in range(len(ERA_ORDER))],
                edgecolor=C_INK, linewidth=1.2)
ax.set_title("Books per Era")
ax.tick_params(axis="x", rotation=30); ax.set_ylabel("# Books")
for b in bars_e:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+5,
            f"{int(b.get_height()):,}", ha="center", fontsize=8)

ax = axes[1]
ax.bar(dec_cnt.index, dec_cnt.values, width=8,
       color=C_BLUE, edgecolor=C_INK, linewidth=0.7, alpha=0.8)
ax.set_title("Books Published per Decade (1900–2020)")
ax.set_xlabel("Decade"); ax.set_ylabel("# Books")

ax = axes[2]
ax.plot(dec_rat.index, dec_rat.values, color=C_RED, lw=2, marker="o", ms=5)
ax.axhline(df["average_rating"].mean(), color=C_YELLOW, lw=1.5, ls="--", label="Overall mean")
ax.set_title("Avg Rating by Decade")
ax.set_xlabel("Decade"); ax.set_ylabel("Average Rating")
ax.legend()

savefig("06_era.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 07 — Mood Analysis  (mood multi-select)
# ══════════════════════════════════════════════════════════════════
print("[07/11] Mood Analysis")

mood_ctr = Counter()
for ml in df["mood_tags"]: mood_ctr.update(ml)
moods     = list(MOOD_MAP.keys())
mood_vals = [mood_ctr.get(m, 0) for m in moods]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("07 · Mood Analysis  ◀ MOOD multi-select ▶", fontsize=14, fontweight="bold")

ax = axes[0]
bars_m = ax.barh(moods, mood_vals,
                 color=[PAL[i % len(PAL)] for i in range(len(moods))],
                 edgecolor=C_INK, linewidth=1)
ax.set_title("Books Tagged per Mood\n(via description keyword matching)")
ax.set_xlabel("# Books")
for b, v in zip(bars_m, mood_vals):
    ax.text(v+5, b.get_y()+b.get_height()/2, str(v), va="center", fontsize=9)

# Mood vs rating
ax2 = axes[1]
mrat = []
for m in moods:
    mask = df["mood_tags"].apply(lambda ml: m in ml)
    avg  = df.loc[mask, "average_rating"].mean()
    mrat.append((m, avg if not pd.isna(avg) else 0))
mrat.sort(key=lambda x: x[1])
ml2, mv2 = zip(*mrat)
bars_mr = ax2.barh(ml2, mv2, color=C_YELLOW, edgecolor=C_INK, linewidth=1)
ax2.axvline(df["average_rating"].mean(), color=C_RED, lw=2, ls="--", label="Overall mean")
ax2.set_xlim(3.0, 4.4)
ax2.set_title("Avg Rating per Mood Tag")
ax2.set_xlabel("Average Rating"); ax2.legend()
for b, v in zip(bars_mr, mv2):
    ax2.text(v+0.01, b.get_y()+b.get_height()/2, f"{v:.2f}", va="center", fontsize=9)

savefig("07_moods.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 08 — Author Analysis
# ══════════════════════════════════════════════════════════════════
print("[08/11] Author Analysis")

auth_ctr = Counter()
for al in df["authors_list"]: auth_ctr.update(al)
top20a = auth_ctr.most_common(20)
a_labels, a_counts = zip(*top20a)
a_ratings = {}
for a in a_labels:
    mask = df["authors_list"].apply(lambda al: a in al)
    a_ratings[a] = df.loc[mask, "average_rating"].mean()

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("08 · Author Analysis", fontsize=14, fontweight="bold")

ax = axes[0]
ax.barh(a_labels[::-1], a_counts[::-1],
        color=[PAL[i % len(PAL)] for i in range(len(a_labels))][::-1],
        edgecolor=C_INK, linewidth=1)
ax.set_title("Top 20 Most Represented Authors")
ax.set_xlabel("# Books in Catalog")

ax2 = axes[1]
sorted_ar = sorted(zip(a_labels, [a_ratings[a] for a in a_labels]), key=lambda x: x[1])
sl, sv = zip(*sorted_ar)
bars_a = ax2.barh(sl, sv, color=C_YELLOW, edgecolor=C_INK, linewidth=1)
ax2.axvline(df["average_rating"].mean(), color=C_RED, lw=2, ls="--", label="Overall mean")
ax2.set_xlim(3.0, 4.7)
ax2.set_title("Avg Rating — Top 20 Authors")
ax2.set_xlabel("Average Rating"); ax2.legend()
for b, v in zip(bars_a, sv):
    ax2.text(v+0.01, b.get_y()+b.get_height()/2, f"{v:.2f}", va="center", fontsize=9)

savefig("08_authors.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 09 — Popularity Breakdown
# ══════════════════════════════════════════════════════════════════
print("[09/11] Popularity Breakdown")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("09 · Popularity & Engagement Analysis", fontsize=14, fontweight="bold")

# Log ratings
ax = axes[0][0]
ax.hist(df["log_ratings"], bins=50, color=C_RED, edgecolor=C_INK, linewidth=0.7)
ax.set_title("Log(Ratings Count) Distribution")
ax.set_xlabel("log(1 + Ratings Count)"); ax.set_ylabel("# Books")

# Stacked star breakdown for top 10 books
ax = axes[0][1]
top10 = df.nlargest(10, "ratings_count")[
    ["title","ratings_1","ratings_2","ratings_3","ratings_4","ratings_5"]].copy()
top10["title"] = top10["title"].str[:22] + "…"
bottom = np.zeros(len(top10))
star_cols  = [C_RED, "#FF8C00", C_YELLOW, "#66BB6A", C_BLUE]
for i, col in enumerate(["ratings_1","ratings_2","ratings_3","ratings_4","ratings_5"]):
    ax.bar(top10["title"], top10[col], bottom=bottom,
           label=f"{i+1}★", color=star_cols[i], edgecolor="none")
    bottom += top10[col].values
ax.set_title("Star Breakdown — Top 10 Most Rated")
ax.tick_params(axis="x", rotation=45); ax.legend(loc="upper right", fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x/1e6:.1f}M"))

# Pages vs popularity
ax = axes[1][0]
s4 = df[df["pages"].between(50,1500)].sample(min(2000,len(df)), random_state=99)
ax.scatter(s4["pages"], np.log1p(s4["ratings_count"]),
           alpha=0.3, s=8, c=C_BLUE, edgecolors="none")
ax.set_title("Page Count vs. log(Popularity)")
ax.set_xlabel("Pages"); ax.set_ylabel("log(Ratings Count)")

# Median popularity by era
ax = axes[1][1]
era_pop = df.groupby("era")["ratings_count"].median().reindex(ERA_ORDER[:-1], fill_value=0)
bars_ep = ax.bar(era_pop.index, era_pop.values,
                 color=C_YELLOW, edgecolor=C_INK, linewidth=1.2)
ax.set_title("Median Ratings Count by Era")
ax.set_xlabel("Era"); ax.set_ylabel("Median Ratings Count")
ax.tick_params(axis="x", rotation=30)
for b in bars_ep:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+200,
            f"{int(b.get_height()):,}", ha="center", fontsize=8)

savefig("09_popularity.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 10 — Language & Description Quality
# ══════════════════════════════════════════════════════════════════
print("[10/11] Language & Description Quality")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("10 · Language & Description Quality", fontsize=14, fontweight="bold")

ax = axes[0]
lang_c = df["language_code"].value_counts().head(12)
ax.bar(lang_c.index, lang_c.values,
       color=[PAL[i % len(PAL)] for i in range(len(lang_c))],
       edgecolor=C_INK, linewidth=1)
ax.set_title("Books by Language Code")
ax.set_xlabel("Language Code"); ax.set_ylabel("# Books")
ax.tick_params(axis="x", rotation=25)
for i, (lbl, val) in enumerate(lang_c.items()):
    ax.text(i, val + 30, f"{val:,}", ha="center", fontsize=8)

ax2 = axes[1]
desc_len = df["description"].dropna().str.len()
ax2.hist(desc_len, bins=50, color=C_RED, edgecolor=C_INK, linewidth=0.7)
ax2.axvline(desc_len.mean(), color=C_BLUE, lw=2, ls="--",
            label=f"Mean  {desc_len.mean():.0f} chars")
ax2.axvline(desc_len.median(), color=C_YELLOW, lw=2, ls="--",
            label=f"Median {desc_len.median():.0f} chars")
ax2.set_title("Description Length Distribution")
ax2.set_xlabel("Character Count"); ax2.set_ylabel("# Books")
ax2.legend()

savefig("10_language_desc.png")


# ══════════════════════════════════════════════════════════════════
#  PLOT 11 — Feature Correlation Heatmap
# ══════════════════════════════════════════════════════════════════
print("[11/11] Correlation Heatmap")

num_cols = ["average_rating", "ratings_count", "pages", "pub_year",
            "ratings_1", "ratings_2", "ratings_3", "ratings_4", "ratings_5",
            "work_text_reviews_count", "books_count"]
corr = df[num_cols].corr()

fig, ax = plt.subplots(figsize=(11, 9))
fig.suptitle("11 · Numeric Feature Correlation Matrix", fontsize=14, fontweight="bold")
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(len(num_cols))); ax.set_xticklabels(num_cols, rotation=45, ha="right")
ax.set_yticks(range(len(num_cols))); ax.set_yticklabels(num_cols)
plt.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
for i in range(len(num_cols)):
    for j in range(len(num_cols)):
        v = corr.values[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                color="white" if abs(v) > 0.5 else C_INK)

savefig("11_correlation.png")


# ══════════════════════════════════════════════════════════════════
#  CONSOLE SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  EDA SUMMARY & FORM → FEATURE MAPPING")
print("="*60)
print(f"""
DATASET
  Books          : {len(df):,}
  Columns        : {df.shape[1]}
  Unique genres  : {df['genres_list'].explode().nunique()}
  Unique authors : {df['authors_list'].explode().nunique():,}
  Books w/ pages : {df['pages'].notna().sum():,} ({df['pages'].notna().mean()*100:.1f}%)
  Books w/ desc  : {df['description'].notna().sum():,} ({df['description'].notna().mean()*100:.1f}%)
  Pub year span  : {int(df['pub_year'].dropna().min())} – {int(df['pub_year'].dropna().max())}

RATING STATS (average_rating)
  Mean   : {df['average_rating'].mean():.3f}
  Median : {df['average_rating'].median():.3f}
  Std    : {df['average_rating'].std():.3f}
  Range  : {df['average_rating'].min():.2f} – {df['average_rating'].max():.2f}
  Note   : 80% of books fall between 3.5–4.5 ★
           → Recommended slider range: 3.0 – 4.5

PAGE STATS (pages)
  Median  : {df['pages'].median():.0f} pp
  Q1 / Q3 : {df['pages'].quantile(0.25):.0f} / {df['pages'].quantile(0.75):.0f} pp
  Note    : Short < 300, Medium 300-500, Long 500-700, Epic 700+

FORM FIELD → DATA COLUMN MAPPING
  [GENRE multi-select]     → genres_list   (list parsed from genres col)
  [MOOD multi-select]      → mood_tags     (derived from description NLP)
  [MIN RATING slider]      → average_rating (range: 3.0 – 4.5)
  [LIGHT ↔ HEAVY slider]  → pages          (Q1=247, Median=336, Q3=449)
  [RECENT ↔ OLD slider]   → original_publication_year
  [Format radio]           → NOT in dataset (needs external enrichment)
  [Language filter]        → language_code  (93%+ are 'eng')

RECOMMENDED EXTRA FORM FIELDS for Model Training
  ✓ Series preference (books_count > 1 suggests part of a series)
  ✓ Review depth (work_text_reviews_count → reader engagement)
  ✓ Popularity weight (ratings_count → social proof signal)
  ✓ Author preference (free-text or author autocomplete)
  ✓ Language preference (language_code filter)

MODEL SIGNAL QUALITY
  STRONG  : genres_list, description (TF-IDF / embeddings), average_rating
  MEDIUM  : pages, pub_year, ratings_count, authors_list
  WEAK    : language_code (93% eng), books_count
  DERIVED : mood_tags (keyword NLP), rating_tier, page_bucket, era
""")

print(f"  Plots saved to: {OUT_DIR}/")
print("="*60)
