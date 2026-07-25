"""
Employmentmaxxing — Hacker News Who's Hiring Scraper
Parses the monthly HN "Who is Hiring?" threads via the Algolia API (free, official).
"""

import re
import requests
import traceback
from datetime import datetime

from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end
from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote


# HN Algolia search API
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="

# Keywords that indicate the comment is relevant to us
RELEVANT_KEYWORDS = [
    "intern", "internship", "co-op", "junior", "new grad",
    "entry level", "entry-level", "student",
    "machine learning", "ml", "ai ", "artificial intelligence",
    "deep learning", "nlp", "computer vision", "pytorch", "tensorflow",
    "quantum", "qiskit", "cirq",
    "software engineer", "swe", "full stack", "backend", "frontend",
]


def _find_latest_hiring_thread() -> dict | None:
    """Find the most recent 'Who is hiring?' thread."""
    try:
        resp = requests.get(HN_SEARCH_URL, params={
            "query": "\"Ask HN: Who is hiring?\"",
            "tags": "story",
            "numericFilters": "created_at_i>0",
            "hitsPerPage": 5,
        }, timeout=15)

        if resp.status_code != 200:
            return None

        hits = resp.json().get("hits", [])
        # Find the most recent one authored by "whoishiring"
        for hit in hits:
            if hit.get("author") == "whoishiring" or "who is hiring" in hit.get("title", "").lower():
                return hit

        # Fallback: just use the most recent hit
        return hits[0] if hits else None

    except Exception as e:
        print(f"   ❌ Error finding HN thread: {e}")
        return None


def _fetch_comments(story_id: int, page: int = 0) -> list[dict]:
    """Fetch comments from a HN story via Algolia."""
    try:
        resp = requests.get(HN_SEARCH_URL, params={
            "tags": f"comment,story_{story_id}",
            "hitsPerPage": 100,
            "page": page,
        }, timeout=15)

        if resp.status_code != 200:
            return []

        return resp.json().get("hits", [])

    except Exception as e:
        print(f"   ❌ Error fetching HN comments: {e}")
        return []


def _is_relevant_comment(text: str) -> bool:
    """Check if a comment is relevant (contains our target keywords)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in RELEVANT_KEYWORDS)


def _parse_hn_comment(comment: dict) -> dict | None:
    """Parse a HN hiring comment into a job listing."""
    text = comment.get("comment_text", "")
    if not text:
        return None

    # HN comments often start with "Company Name | Location | ..."
    # or "Company Name (https://...) | ..."
    lines = text.replace("<p>", "\n").split("\n")
    first_line = re.sub(r"<[^>]+>", "", lines[0]).strip()

    # Try to extract company name from first line
    parts = re.split(r"\s*[|]\s*", first_line)
    company = parts[0].strip() if parts else "Unknown"

    # Remove markdown/html artifacts from company name
    company = re.sub(r"\(https?://[^\)]+\)", "", company).strip()
    company = re.sub(r"<[^>]+>", "", company).strip()
    company = company[:100]  # Truncate if too long

    if not company or len(company) < 2:
        return None

    # Extract location from parts
    location = ""
    for part in parts[1:]:
        part_clean = part.strip().lower()
        if any(kw in part_clean for kw in ["remote", "onsite", "hybrid", "sf", "nyc", "seattle", "austin", "boston"]):
            location = part.strip()
            break

    # Extract URLs from comment
    urls = re.findall(r'href="(https?://[^"]+)"', text)
    if not urls:
        urls = re.findall(r"(https?://\S+)", text)
    apply_url = urls[0] if urls else f"{HN_ITEM_URL}{comment.get('objectID', '')}"

    # Build title from context
    title_parts = []
    for part in parts[1:]:
        part_clean = re.sub(r"<[^>]+>", "", part).strip()
        if part_clean and part_clean != location:
            title_parts.append(part_clean)
    title = " | ".join(title_parts[:3]) if title_parts else f"Open Position at {company}"
    title = title[:200]

    # Clean description
    description = re.sub(r"<[^>]+>", " ", text)
    description = re.sub(r"\s+", " ", description).strip()

    return {
        "id": generate_job_id(company, title, "hn"),
        "title": title,
        "company": company,
        "location": location or "See listing",
        "is_remote": is_remote(title, location, description),
        "description": description[:5000],
        "apply_url": apply_url,
        "salary_min": None,
        "salary_max": None,
        "date_posted": comment.get("created_at", ""),
        "source": "hackernews",
        "experience_level": detect_experience_level(title, description),
        "job_type": classify_job_type(title, description),
        "raw_data": {
            "hn_id": comment.get("objectID"),
            "author": comment.get("author"),
        },
    }


def run_hn_scrape() -> dict:
    """
    Scrape the latest HN 'Who is Hiring?' thread.
    Returns stats dict.
    """
    log_id = log_scrape_start("hackernews")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    try:
        print("📰 Finding latest HN 'Who is Hiring?' thread...")
        thread = _find_latest_hiring_thread()

        if not thread:
            error_msg = "Could not find HN hiring thread"
            print(f"   ❌ {error_msg}")
            stats["errors"].append(error_msg)
            log_scrape_end(log_id, 0, 0, 0, stats["errors"])
            return stats

        story_id = thread.get("objectID")
        print(f"   📋 Found thread: {thread.get('title', 'Unknown')} (ID: {story_id})")

        # Fetch multiple pages of comments
        all_comments = []
        for page in range(3):  # First 300 comments
            comments = _fetch_comments(int(story_id), page)
            if not comments:
                break
            all_comments.extend(comments)

        print(f"   📋 Fetched {len(all_comments)} comments")

        # Filter and parse relevant comments
        for comment in all_comments:
            text = comment.get("comment_text", "")
            if not text or not _is_relevant_comment(text):
                continue

            # Skip replies (top-level comments are job postings)
            if comment.get("parent_id") and str(comment.get("parent_id")) != str(story_id):
                continue

            job = _parse_hn_comment(comment)
            if job:
                is_new = insert_job(job)
                stats["jobs_found"] += 1
                if is_new:
                    stats["jobs_new"] += 1
                else:
                    stats["jobs_duplicate"] += 1

    except Exception as e:
        error_msg = f"Error in HN scrape: {str(e)}"
        print(f"   ❌ {error_msg}")
        stats["errors"].append(error_msg)
        traceback.print_exc()

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ HN scrape complete: {stats['jobs_new']} new / {stats['jobs_duplicate']} dupes")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_hn_scrape()
    print(stats)
