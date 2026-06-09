import json
import random
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from transformers import AutoTokenizer

# =====================================================
# CONFIG
# =====================================================

# (school_name, url) — names mirror planning.md so output is self-describing.
SCHOOLS = [
    ("Hunter College",      "https://www.ratemyprofessors.com/school/226"),
    ("Queens College",      "https://www.ratemyprofessors.com/school/231"),
    ("Baruch College",      "https://www.ratemyprofessors.com/school/222"),
    ("Columbia University", "https://www.ratemyprofessors.com/school/278"),
    ("Binghamton",          "https://www.ratemyprofessors.com/school/958"),
    ("Stony Brook",         "https://www.ratemyprofessors.com/school/971"),
    ("Brooklyn College",    "https://www.ratemyprofessors.com/school/223"),
    ("NYU",                 "https://www.ratemyprofessors.com/school/675"),
    ("Cornell",             "https://www.ratemyprofessors.com/school/298"),
    ("CCNY",                "https://www.ratemyprofessors.com/school/224"),
]

CHUNK_SIZE = 512          # max tokens per chunk (planning.md: 256-512)
OVERLAP = 100             # token overlap when a review must be split
LOAD_MORE_CLICKS = 8      # how many times to click "Load More Ratings" per school
HEADLESS = True

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# TOKENIZER  (matches the embedding model in planning.md)
# =====================================================

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

# =====================================================
# CLEANING
# =====================================================

def clean(text):
    if not text:
        return ""
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_float(text):
    """Pull the first number (e.g. an overall rating) out of a string."""
    if not text:
        return None
    m = re.search(r"\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def parse_date(text):
    if not text:
        return None
    m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}\w*,?\s+\d{4}",
        text,
    )
    return m.group(0) if m else None

# =====================================================
# SCRAPING  (structured DOM extraction)
# =====================================================

# Stable styled-component prefixes (the -xxxxx-0 hash suffix is ignored).
EXTRACT_JS = """
() => {
  const txt = (el) => (el ? el.textContent.replace(/\\s+/g, ' ').trim() : null);
  const q  = (root, sel) => root.querySelector(sel);
  const qa = (root, sel) => Array.from(root.querySelectorAll(sel));

  // ---- School-level summary (page header) ----
  const overall = txt(q(document, '[class*="OverallRating__Number"]'));

  const categories = qa(document, '[class*="CategoryGrade__CategoryGradeContainer"]')
    .map((c) => ({
      name:  txt(q(c, '[class*="CategoryGrade__CategoryTitle"]')),
      grade: txt(q(c, '[class*="GradeSquare__ColoredSquare"]')),
    }))
    .filter((c) => c.name && c.grade);

  // ---- Individual reviews ----
  const reviews = qa(document, '[class*="SchoolRating__SchoolRatingContainer"]')
    .map((r) => ({
      overall: txt(q(r, '[class*="SchoolRating__OverallRatingContainer"]')),
      header:  txt(q(r, '[class*="SchoolRating__RatingHeader"]')),
      comment: txt(q(r, '[class*="SchoolRating__RatingComment"]')),
      sliders: qa(r, '[class*="DisplaySlider__DisplaySliderContainer"]')
                 .map((s) => txt(s)).filter(Boolean),
    }))
    .filter((r) => r.comment);

  return { overall, categories, reviews };
}
"""


def dismiss_popups(page):
    """Close the cookie / GDPR consent overlay (it blocks clicks otherwise)."""
    for name in ["Reject All", "Allow All", "Confirm My Choices", "Close"]:
        try:
            page.get_by_role("button", name=name).click(timeout=2500)
            return
        except Exception:
            pass


def load_more(page, clicks):
    """Click the 'Show More' button to paginate in more reviews."""
    for _ in range(clicks):
        try:
            btn = page.get_by_role("button", name="Show More")
            btn.scroll_into_view_if_needed(timeout=3000)
            btn.click(timeout=3000)
            page.wait_for_timeout(1800)
        except Exception:
            break  # button gone -> no more pages


def scrape(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    dismiss_popups(page)
    # Wait for the review list to render (styled-component prefix match).
    try:
        page.wait_for_selector('[class*="SchoolRating__SchoolRatingContainer"]', timeout=15000)
    except Exception:
        print(f"  ! No review containers found for {url}")
    load_more(page, LOAD_MORE_CLICKS)
    return page.evaluate(EXTRACT_JS)

# =====================================================
# CHUNKING  (review-aware: keep each review whole when it fits)
# =====================================================

def chunk_review(text):
    """Return one chunk if the review fits in CHUNK_SIZE tokens,
    otherwise split with OVERLAP so no review is silently truncated."""
    tokens = tokenizer.encode(text, add_special_tokens=False)
    if len(tokens) <= CHUNK_SIZE:
        return [text]

    chunks, start = [], 0
    while start < len(tokens):
        window = tokens[start:start + CHUNK_SIZE]
        chunks.append(tokenizer.decode(window, skip_special_tokens=True))
        start += CHUNK_SIZE - OVERLAP
    return chunks

# =====================================================
# MAIN PIPELINE
# =====================================================

def build():
    structured_dataset = []
    all_chunks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        for i, (name, url) in enumerate(SCHOOLS):
            print(f"[{i + 1}/{len(SCHOOLS)}] {name} -> {url}")
            try:
                data = scrape(page, url)
            except Exception as e:
                print(f"  ! Failed to scrape {url}: {e}")
                continue

            # ---- Clean school-level summary ----
            overall_quality = first_float(data.get("overall"))
            ratings = {"overall_quality": overall_quality}
            for c in data.get("categories", []):
                key = clean(c["name"]).lower().replace(" ", "_")
                ratings[key] = first_float(c["grade"])

            # ---- Clean reviews ----
            reviews = []
            for r in data.get("reviews", []):
                comment = clean(r.get("comment"))
                if len(comment) < 30:
                    continue
                reviews.append({
                    "rating": first_float(r.get("overall")),
                    "date": parse_date(r.get("header")),
                    "categories": [clean(s) for s in r.get("sliders", [])],
                    "text": comment,
                })

            structured_dataset.append({
                "school": name,
                "source": url,
                "ratings": ratings,
                "review_count": len(reviews),
                "reviews": reviews,
            })

            # Save raw extraction per school for debugging / reproducibility.
            (RAW_DIR / f"school_{i}_{name.replace(' ', '_')}.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            # ---- Build chunks ----
            # 1) One dedicated "summary" chunk so the overall rating + category
            #    grades are retrievable on their own (fixes the "ratings are a
            #    different format than review text" challenge in planning.md).
            grade_lines = [
                f"{k.replace('_', ' ').title()}: {v}"
                for k, v in ratings.items() if v is not None
            ]
            summary_text = (
                f"{name} - overall student ratings on RateMyProfessors.\n"
                + "\n".join(grade_lines)
            )
            all_chunks.append({
                "school": name,
                "source": url,
                "type": "summary",
                "rating": overall_quality,
                "date": None,
                "text": summary_text,
            })

            # 2) Review chunks (kept whole unless too long).
            for r in reviews:
                for c in chunk_review(r["text"]):
                    all_chunks.append({
                        "school": name,
                        "source": url,
                        "type": "review",
                        "rating": r["rating"],
                        "date": r["date"],
                        "text": c,
                    })

            print(f"  overall={overall_quality}  reviews={len(reviews)}")

        browser.close()

    # =====================================================
    # SAVE OUTPUTS
    # =====================================================
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "structured.json").write_text(
        json.dumps(structured_dataset, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / "chunks.json").write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print(f"Schools scraped : {len(structured_dataset)}")
    print(f"Total chunks    : {len(all_chunks)}")
    print(f"Outputs         : {DATA_DIR / 'structured.json'}, {DATA_DIR / 'chunks.json'}")
    print("=" * 60)

    # ---- Sanity checks against the targets ----
    low = [d["school"] for d in structured_dataset if d["review_count"] < 5]
    if low:
        print(f"\n!! These schools have fewer than 5 reviews: {', '.join(low)}")
        print("   Increase LOAD_MORE_CLICKS and re-run.")
    if len(all_chunks) < 50:
        print(f"\n!! Only {len(all_chunks)} chunks (< 50). Increase LOAD_MORE_CLICKS and re-run.")

    # ---- 5 random chunks to eyeball quality ----
    print("\n5 RANDOM CHUNKS:\n")
    for c in random.sample(all_chunks, min(5, len(all_chunks))):
        print("-" * 60)
        print(f"[{c['type']}] {c['school']} (rating={c['rating']}, date={c['date']})")
        print(c["text"][:500])


if __name__ == "__main__":
    build()
