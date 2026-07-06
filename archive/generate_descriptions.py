import csv
import json
import os
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_ROOT = _HERE.parent
BOOKS_CSV = _ROOT / "backend" / "db" / "books.csv"
OUTPUT_CSV = _ROOT / "backend" / "db" / "books_with_descriptions.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"

# We will generate LLM descriptions for the top N most popular books.
# The recommendation engine sorts by rating/popularity, so the recommended books
# will almost always come from the top 1500. The rest will get a high-quality template.
LIMIT_LLM = 50
CONCURRENCY = 5  # Safe concurrency for 16GB RAM M2 Pro

TEMPLATES = [
    "A captivating narrative by {author} that has resonated with readers globally.",
    "A highly regarded work by {author}, offering a memorable and engaging reading experience.",
    "An impactful story by {author} that stands as a notable entry in its genre.",
    "A brilliant publication by {author} that continues to engage and inspire audiences.",
    "A compelling read by {author} exploring profound themes with memorable character depth.",
    "A beautifully crafted book by {author} that captures the imagination from start to finish."
]

def get_fallback_description(author, book_id):
    if not author or author.lower() == "unknown":
        author = "an acclaimed writer"
    idx = book_id % len(TEMPLATES)
    return TEMPLATES[idx].format(author=author)

def generate_description_llm(title, author):
    prompt = (
        f"Describe the book '{title}' by {author} in one short, engaging sentence of 12 to 20 words. "
        "Do not use introductory text, quotes, or markdown. Focus purely on the plot or essence of the book."
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 450,  # Give deepseek-r1 enough room to think and output
            "top_k": 20,
            "top_p": 0.9
        }
    }
    
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data.get("response", "").strip()
            
            # DeepSeek-r1 outputs thinking process inside <think>...</think> tags.
            # We must strip them out to get the clean description.
            if "<think>" in raw_text:
                if "</think>" in raw_text:
                    parts = raw_text.split("</think>")
                    raw_text = parts[-1].strip()
                else:
                    # Incomplete thinking block (cut off), discard and use fallback
                    return None
            
            # Clean up double quotes and stray newlines
            raw_text = raw_text.replace('"', '').replace('\n', ' ').strip()
            
            # Remove leading/trailing quote marks if the model still generated them
            raw_text = raw_text.strip("'\"")
            
            if len(raw_text) > 10:
                return raw_text
    except Exception as e:
        # Silently fail and let caller use fallback
        pass
    
    return None

def process_book(row, index, total, use_llm):
    book_id = int(row["id"])
    title = row.get("original_title") or row.get("title") or "Unknown Title"
    author = row.get("authors", "").split(",")[0].strip()
    
    desc = None
    if use_llm:
        print(f"[{index}/{total}] Generating LLM description for: {title} by {author}...", flush=True)
        desc = generate_description_llm(title, author)
    
    if not desc:
        desc = get_fallback_description(author, book_id)
        
    row["description"] = desc
    return row

def main():
    print("═" * 60)
    print("  GOODBOOKS — Description Generator using DeepSeek-r1:8b")
    print("═" * 60)
    
    if not BOOKS_CSV.exists():
        print(f"Error: {BOOKS_CSV} does not exist.")
        sys.exit(1)
        
    # Read books
    books = []
    with open(BOOKS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            books.append(r)
            
    print(f"Read {len(books)} books from catalog.")
    
    # Sort books by popularity (ratings_count) to identify the top books
    # so we prioritize them for LLM generation.
    def get_ratings_count(b):
        try:
            return int(b.get("ratings_count") or 0)
        except ValueError:
            return 0
            
    books.sort(key=get_ratings_count, reverse=True)
    
    # Track the original index to restore order at the end
    for idx, b in enumerate(books):
        b["_sort_order"] = idx
        
    # Determine which books get LLM generation
    llm_jobs = []
    fallback_jobs = []
    for idx, b in enumerate(books):
        if idx < LIMIT_LLM:
            llm_jobs.append(b)
        else:
            fallback_jobs.append(b)
            
    print(f"Prioritized top {len(llm_jobs)} books for DeepSeek generation.", flush=True)
    print(f"Remaining {len(fallback_jobs)} books will receive high-quality templates.", flush=True)
    
    results = []
    
    # Process fallback books first (instant)
    print("Processing fallback templates...", flush=True)
    for idx, b in enumerate(fallback_jobs):
        b["description"] = get_fallback_description(b.get("authors", "").split(",")[0].strip(), int(b["id"]))
        results.append(b)
        
    # Process LLM books in parallel
    print(f"Starting parallel LLM generation with concurrency={CONCURRENCY}...", flush=True)
    total_llm = len(llm_jobs)
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {
            executor.submit(process_book, b, idx + 1, total_llm, True): b
            for idx, b in enumerate(llm_jobs)
        }
        
        completed_count = 0
        for future in as_completed(futures):
            row = future.result()
            results.append(row)
            completed_count += 1
            print(f"  → Completed {completed_count}/{total_llm} LLM generations...", flush=True)
                
    # Restore original order
    results.sort(key=lambda x: x["_sort_order"])
    
    # Write output
    output_fields = fieldnames + ["description"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
        
    print("═" * 60)
    print(f"Successfully wrote output to {OUTPUT_CSV}")
    print("═" * 60)

if __name__ == "__main__":
    main()
