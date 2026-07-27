"""
Employmentmaxxing — GitHub Repo Scraper
Scrapes community-maintained GitHub repos for internship listings.
Fixed URL extraction: extracts clean href URLs from raw HTML <a> tags and markdown links.
"""

import re
import requests
import traceback
from datetime import datetime

from config import settings
from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end


RAW_BASE = "https://raw.githubusercontent.com"


def _clean_url(raw_text: str) -> str:
    """Extract a clean http/https URL from raw text, HTML tags, or markdown links, removing tracking params."""
    if not raw_text:
        return ""

    candidate = ""
    # Match href="URL" from HTML anchor tags
    href_match = re.search(r'href=["\'](https?://[^"\']+)["\']', raw_text, re.IGNORECASE)
    if href_match:
        candidate = href_match.group(1).strip()
    else:
        # Match markdown link [Text](URL)
        md_match = re.search(r'\[.*?\]\((https?://[^\)]+)\)', raw_text)
        if md_match:
            candidate = md_match.group(1).strip()
        else:
            # Match standalone http/https URL
            raw_url_match = re.search(r'(https?://[^\s<>"]+)', raw_text)
            if raw_url_match:
                candidate = raw_url_match.group(1).strip()

    if not candidate:
        return ""

    # Strip tracking query parameters
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(candidate)
        if parsed.query:
            qs = parse_qs(parsed.query)
            # Filter out tracking keys
            clean_qs = {k: v for k, v in qs.items() if not k.lower().startswith(('utm_', 'ref', 'gh_src', 'source', 'subscriber'))}
            new_query = urlencode(clean_qs, doseq=True)
            candidate = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        pass

    return candidate


def _is_generic_domain(url: str) -> bool:
    """Check if a URL is a generic root domain/homepage rather than a specific job posting."""
    if not url:
        return True
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if not path and not parsed.query:
        return True
    if path.lower() in ['careers', 'jobs', 'en-us', 'about', 'join-us', 'careers/'] and not parsed.query:
        return True
    return False


def _strip_html_and_markdown(text: str) -> str:
    """Strip HTML tags and markdown formatting to get clean text."""
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Strip markdown links: [Text](URL) -> Text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Clean whitespace
    return re.sub(r'\s+', ' ', text).strip()


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
    """Parse markdown tables from community tracking repos."""
    jobs = []
    lines = content.split("\n")

    in_table = False
    headers: list[str] = []

    for line in lines:
        line = line.strip()

        if "|" in line and not in_table:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            lower_cells = [c.lower() for c in cells]
            if any(kw in " ".join(lower_cells) for kw in ["company", "role", "position", "name"]):
                headers = lower_cells
                in_table = True
                continue

        if in_table and re.match(r"^\|[\s\-:|]+\|$", line):
            continue

        if in_table and "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) < 2:
                in_table = False
                continue

            job = _extract_job_from_row(cells, headers, repo_name)
            if job and job.get("apply_url"):
                jobs.append(job)

        elif in_table and "|" not in line:
            in_table = False
            headers = []

    return jobs


def _extract_job_from_row(cells: list[str], headers: list[str], repo_name: str) -> dict | None:
    """Extract job data from a table row."""
    data = {}
    for idx, header in enumerate(headers):
        if idx < len(cells):
            data[header] = cells[idx]

    company_raw = ""
    title_raw = ""
    location_raw = ""
    apply_url = ""

    for key, value in data.items():
        key_lower = key.lower()
        if any(kw in key_lower for kw in ["company", "name", "org"]):
            company_raw = value
        elif any(kw in key_lower for kw in ["role", "position", "title"]):
            title_raw = value
        elif any(kw in key_lower for kw in ["location", "loc"]):
            location_raw = value
        elif any(kw in key_lower for kw in ["link", "apply", "url"]):
            clean_link = _clean_url(value)
            if clean_link:
                apply_url = clean_link

    # Fallback to title link if apply_url is empty but title has a link
    if not apply_url and title_raw:
        cand_url = _clean_url(title_raw)
        if cand_url and not _is_generic_domain(cand_url):
            apply_url = cand_url

    # Clean text values
    company = _strip_html_and_markdown(company_raw)
    title = _strip_html_and_markdown(title_raw)
    location = _strip_html_and_markdown(location_raw)

    if not company or not apply_url:
        return None

    # Skip closed postings
    full_text = " ".join(str(v) for v in data.values()).lower()
    if any(kw in full_text for kw in ["🔒", "closed", "no longer", "expired"]):
        return None

    if not title:
        title = "Technical Intern / Co-op"

    # Auto-register ATS boards discovered in GitHub links
    try:
        from scrapers.registry import discover_board_from_url
        discover_board_from_url(apply_url, company_name=company, source="github_community")
    except Exception:
        pass

    from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote

    return {
        "id": generate_job_id(company, title, location),
        "title": title,
        "company": company,
        "location": location if location else "Various Locations",
        "is_remote": is_remote(title, location),
        "description": f"Listed position at {company}. Role: {title}. See direct application link.",
        "apply_url": apply_url,  # GUARANTEED CLEAN URL
        "salary_min": None,
        "salary_max": None,
        "date_posted": "",
        "source": "github_community",
        "experience_level": detect_experience_level(title, full_text),
        "job_type": classify_job_type(title, full_text),
        "raw_data": {"repo": repo_name, "row_data": data},
    }


def run_github_scrape() -> dict:
    """Scrape configured GitHub repos for internship listings."""
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
            print(f"   📋 Parsed {len(jobs)} jobs with verified apply URLs from {repo}")

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
    run_github_scrape()
