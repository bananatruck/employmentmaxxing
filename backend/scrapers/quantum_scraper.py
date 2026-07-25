"""
Employmentmaxxing — Quantum Job Board Scraper
Scrapes niche quantum computing job boards for student/intern positions.
"""

import re
import requests
import traceback
from bs4 import BeautifulSoup

from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end
from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote


QUANTUM_SOURCES = [
    {
        "name": "QED-C / Quantum Consortium",
        "url": "https://quantumconsortium.org/newjobs/",
        "type": "html_list",
    },
]

QUANTUM_KEYWORDS = [
    "intern", "internship", "co-op", "student", "junior",
    "entry", "graduate", "research assistant",
]


def _scrape_generic_careers_page(url: str, source_name: str) -> list[dict]:
    """
    Generic scraper for simple career pages.
    Looks for job listing patterns (links with job-related text).
    """
    jobs = []
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Employmentmaxxing/1.0; personal job tracker)"
        })
        if resp.status_code != 200:
            print(f"   ⚠️ HTTP {resp.status_code} from {url}")
            return jobs

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strategy 1: Find job listing links
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]

            if not text or len(text) < 5:
                continue

            text_lower = text.lower()
            # Check if this looks like a job posting link
            if any(kw in text_lower for kw in QUANTUM_KEYWORDS):
                # Build absolute URL
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"

                # Extract company from context
                parent = link.find_parent(["li", "div", "tr", "article"])
                company = ""
                if parent:
                    parent_text = parent.get_text(" ", strip=True)
                    # Try to extract company name (often the first part)
                    parts = re.split(r"[–—\-|:]", parent_text)
                    if len(parts) > 1:
                        company = parts[0].strip()[:100]

                if not company:
                    company = source_name

                job = {
                    "id": generate_job_id(company, text),
                    "title": text[:200],
                    "company": company,
                    "location": "See listing",
                    "is_remote": is_remote(text),
                    "description": f"Quantum computing position from {source_name}. See apply link for details.",
                    "apply_url": href,
                    "salary_min": None,
                    "salary_max": None,
                    "date_posted": "",
                    "source": "quantum_board",
                    "experience_level": detect_experience_level(text),
                    "job_type": "Quantum",
                    "raw_data": {"source": source_name, "url": url},
                }
                jobs.append(job)

    except Exception as e:
        print(f"   ❌ Error scraping {url}: {e}")

    return jobs


def run_quantum_scrape() -> dict:
    """
    Scrape quantum-specific job boards.
    Returns stats dict.
    """
    log_id = log_scrape_start("quantum_boards")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    for source in QUANTUM_SOURCES:
        try:
            print(f"⚛️  Scraping quantum board: {source['name']}")
            jobs = _scrape_generic_careers_page(source["url"], source["name"])
            print(f"   📋 Found {len(jobs)} quantum job listings")

            for job in jobs:
                is_new = insert_job(job)
                stats["jobs_found"] += 1
                if is_new:
                    stats["jobs_new"] += 1
                else:
                    stats["jobs_duplicate"] += 1

        except Exception as e:
            error_msg = f"Error scraping {source['name']}: {str(e)}"
            print(f"   ❌ {error_msg}")
            stats["errors"].append(error_msg)
            traceback.print_exc()

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ Quantum scrape complete: {stats['jobs_new']} new / {stats['jobs_duplicate']} dupes")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_quantum_scrape()
    print(stats)
