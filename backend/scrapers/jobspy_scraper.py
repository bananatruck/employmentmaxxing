"""
Employmentmaxxing — JobSpy Scraper
Scrapes LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter via python-jobspy.
"""

import time
import traceback
from datetime import datetime

from jobspy import scrape_jobs
from config import settings
from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end


# Map jobspy site names to our source names
SITES = ["indeed", "linkedin", "glassdoor", "google", "zip_recruiter"]


def classify_job_type(title: str, description: str = "") -> str:
    """Classify a job into our target categories based on title/description keywords."""
    text = f"{title} {description}".lower()

    quantum_kw = ["quantum", "qiskit", "cirq", "pennylane", "qubit"]
    ai_ml_kw = [
        "machine learning", "deep learning", "ai ", "artificial intelligence",
        "nlp", "natural language", "computer vision", "ml ", "neural network",
        "pytorch", "tensorflow", "llm", "generative ai", "data science",
        "reinforcement learning", "mlops",
    ]
    swe_kw = [
        "software engineer", "software developer", "swe", "full stack",
        "fullstack", "backend", "frontend", "devops", "cloud engineer",
        "platform engineer", "systems engineer",
    ]

    if any(kw in text for kw in quantum_kw):
        return "Quantum"
    if any(kw in text for kw in ai_ml_kw):
        return "AI/ML"
    if any(kw in text for kw in swe_kw):
        return "SWE"
    return "Other"


def detect_experience_level(title: str, description: str = "") -> str:
    """Detect experience level from job title/description."""
    text = f"{title} {description}".lower()

    if any(kw in text for kw in ["intern", "internship"]):
        return "intern"
    if any(kw in text for kw in ["co-op", "coop", "cooperative"]):
        return "co-op"
    if any(kw in text for kw in ["new grad", "new graduate", "entry level", "entry-level", "junior"]):
        return "new_grad"
    return "other"


def is_remote(title: str, location: str = "", description: str = "") -> bool:
    """Check if a job is remote-friendly."""
    text = f"{title} {location} {description}".lower()
    return any(kw in text for kw in ["remote", "work from home", "wfh", "hybrid", "anywhere"])


def run_jobspy_scrape() -> dict:
    """
    Run a full scrape cycle across all configured search queries.
    Returns stats dict: {jobs_found, jobs_new, jobs_duplicate, errors}
    """
    log_id = log_scrape_start("jobspy")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    for query in settings.search_queries:
        for location in settings.search_locations:
            try:
                print(f"🔍 Scraping: '{query}' in '{location}'...")

                results = scrape_jobs(
                    site_name=SITES,
                    search_term=query,
                    location=location,
                    results_wanted=settings.scrape_max_results_per_query,
                    hours_old=24,  # Only jobs from last 24h
                    country_indeed="USA",
                )

                if results is None or results.empty:
                    print(f"   ⚠️ No results for '{query}' in '{location}'")
                    continue

                print(f"   📋 Found {len(results)} results")

                for _, row in results.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company_name", row.get("company", ""))).strip()
                    loc = str(row.get("location", "")).strip()
                    desc = str(row.get("description", "")).strip()

                    if not title or not company:
                        continue

                    job_data = {
                        "id": generate_job_id(company, title, loc),
                        "title": title,
                        "company": company,
                        "location": loc,
                        "is_remote": is_remote(title, loc, desc),
                        "description": desc,
                        "apply_url": str(row.get("job_url", row.get("link", ""))).strip(),
                        "salary_min": _parse_salary(row.get("min_amount")),
                        "salary_max": _parse_salary(row.get("max_amount")),
                        "date_posted": str(row.get("date_posted", "")).strip(),
                        "source": str(row.get("site", "jobspy")).strip(),
                        "experience_level": detect_experience_level(title, desc),
                        "job_type": classify_job_type(title, desc),
                        "raw_data": {
                            "query": query,
                            "location": location,
                            "site": str(row.get("site", "")),
                        },
                    }

                    is_new = insert_job(job_data)
                    stats["jobs_found"] += 1
                    if is_new:
                        stats["jobs_new"] += 1
                    else:
                        stats["jobs_duplicate"] += 1

            except Exception as e:
                error_msg = f"Error scraping '{query}' in '{location}': {str(e)}"
                print(f"   ❌ {error_msg}")
                stats["errors"].append(error_msg)
                traceback.print_exc()

            # Rate limiting between queries
            time.sleep(settings.scrape_delay_seconds)

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ JobSpy scrape complete: {stats['jobs_new']} new / {stats['jobs_duplicate']} dupes / {len(stats['errors'])} errors")
    return stats


def _parse_salary(value) -> int | None:
    """Parse salary value from various formats."""
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "").replace("$", "").strip()))
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_jobspy_scrape()
    print(stats)
