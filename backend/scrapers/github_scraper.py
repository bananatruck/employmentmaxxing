"""
Employmentmaxxing — GitHub Repo Scraper
Scrapes community-maintained GitHub repos for internship listings.
Targets: speedyapply/2027-AI-College-Jobs, speedyapply/2027-SWE-College-Jobs,
         vanshb03/Summer2027-Internships
"""

import re
import requests
import traceback
from datetime import datetime

from config import settings
from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end


# GitHub raw content base URL
RAW_BASE = "https://raw.githubusercontent.com"


def _fetch_readme(repo: str) -> str | None:
    """Fetch the README.md content from a GitHub repo."""
    urls = [
        f"{RAW_BASE}/{repo}/main/README.md",
        f"{RAW_BASE}/{repo}/master/README.md",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except requests.RequestException:
            continue
    return None


def _parse_markdown_table(content: str, repo_name: str) -> list[dict]:
    """
    Parse markdown tables commonly used in these repos.
    Expected format: | Company | Role | Location | Link | Date |
    Handles variations in column order and naming.
    """
    jobs = []
    lines = content.split("\n")

    # Find table header rows
    in_table = False
    headers: list[str] = []

    for i, line in enumerate(lines):
        line = line.strip()

        # Detect table header
        if "|" in line and not in_table:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            # Check if this looks like a header row (contains expected column names)
            lower_cells = [c.lower() for c in cells]
            if any(kw in " ".join(lower_cells) for kw in ["company", "role", "position", "name"]):
                headers = lower_cells
                in_table = True
                continue

        # Skip separator row (|---|---|...)
        if in_table and re.match(r"^\|[\s\-:|]+\|$", line):
            continue

        # Parse data row
        if in_table and "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]

            if len(cells) < 2:
                in_table = False
                continue

            job = _extract_job_from_row(cells, headers, repo_name)
            if job:
                jobs.append(job)

        elif in_table and "|" not in line:
            # End of table
            in_table = False
            headers = []

    return jobs


def _extract_job_from_row(cells: list[str], headers: list[str], repo_name: str) -> dict | None:
    """Extract job data from a table row based on detected headers."""
    data = {}
    for idx, header in enumerate(headers):
        if idx < len(cells):
            data[header] = cells[idx]

    # Map common header variations to our fields
    company = ""
    title = ""
    location = ""
    link = ""

    for key, value in data.items():
        if any(kw in key for kw in ["company", "name", "org"]):
            # Extract text, stripping markdown links
            company = _strip_markdown_link_text(value)
        elif any(kw in key for kw in ["role", "position", "title", "job"]):
            title = _strip_markdown_link_text(value)
            # If the role cell contains a link, use it as the apply URL
            extracted_link = _extract_markdown_link(value)
            if extracted_link:
                link = extracted_link
        elif any(kw in key for kw in ["location", "loc"]):
            location = _strip_markdown_link_text(value)
        elif any(kw in key for kw in ["link", "apply", "url"]):
            link = _extract_markdown_link(value) or value

    # Also check if company cell has a link
    for key, value in data.items():
        if any(kw in key for kw in ["company", "name"]) and not link:
            extracted_link = _extract_markdown_link(value)
            if extracted_link:
                link = extracted_link

    if not company or (not title and not link):
        return None

    # Skip entries marked as closed
    full_text = " ".join(str(v) for v in data.values()).lower()
    if any(kw in full_text for kw in ["🔒", "closed", "no longer", "expired"]):
        return None

    if not title:
        title = "Various Positions"

    from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote

    return {
        "id": generate_job_id(company, title, location),
        "title": title,
        "company": company,
        "location": location if location else "Various / See Link",
        "is_remote": is_remote(title, location),
        "description": f"Listed on community tracker: {repo_name}. Check the apply link for full details.",
        "apply_url": link,
        "salary_min": None,
        "salary_max": None,
        "date_posted": "",
        "source": "github_community",
        "experience_level": detect_experience_level(title, full_text),
        "job_type": classify_job_type(title, full_text),
        "raw_data": {"repo": repo_name, "row_data": data},
    }


def _strip_markdown_link_text(text: str) -> str:
    """Extract display text from markdown links: [text](url) → text"""
    match = re.search(r"\[([^\]]+)\]", text)
    return match.group(1).strip() if match else text.strip()


def _extract_markdown_link(text: str) -> str:
    """Extract URL from markdown links: [text](url) → url"""
    match = re.search(r"\[.*?\]\((https?://[^\)]+)\)", text)
    return match.group(1).strip() if match else ""


def run_github_scrape() -> dict:
    """
    Scrape all configured GitHub repos for internship listings.
    Returns stats dict.
    """
    log_id = log_scrape_start("github_community")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    for repo in settings.github_repos:
        try:
            print(f"🐙 Scraping GitHub repo: {repo}")
            content = _fetch_readme(repo)

            if not content:
                error_msg = f"Failed to fetch README from {repo}"
                print(f"   ❌ {error_msg}")
                stats["errors"].append(error_msg)
                continue

            jobs = _parse_markdown_table(content, repo)
            print(f"   📋 Parsed {len(jobs)} jobs from {repo}")

            for job in jobs:
                is_new = insert_job(job)
                stats["jobs_found"] += 1
                if is_new:
                    stats["jobs_new"] += 1
                else:
                    stats["jobs_duplicate"] += 1

        except Exception as e:
            error_msg = f"Error scraping {repo}: {str(e)}"
            print(f"   ❌ {error_msg}")
            stats["errors"].append(error_msg)
            traceback.print_exc()

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ GitHub scrape complete: {stats['jobs_new']} new / {stats['jobs_duplicate']} dupes")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_github_scrape()
    print(stats)
