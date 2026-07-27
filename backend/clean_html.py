"""
Employmentmaxxing — Thorough HTML & Senior Role Filter Sanitizer
Strips raw HTML tags, unescapes entities, purges Senior/Lead/Manager roles, and verifies direct URLs.
"""

import re
import html
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import database

SENIOR_EXCLUSIONS = [
    "senior", "sr.", "sr ", "lead", "principal", "director", "manager", "vp",
    "vice president", "head of", "staff", "architect", "executive", "chief",
]

ALLOWED_STUDENT_KWS = ["intern", "internship", "student", "co-op", "coop", "entry"]


EXP_EXCLUSION_PATTERNS = [
    r"\b(?:5|6|7|8|9|10|\d{2})\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b",
    r"\b5\s*\+\s*years\b",
    r"\b5\s*to\s*10\s*years\b",
    r"\b5-7\s*years\b",
    r"\b5-10\s*years\b",
    r"\bminimum\s*of\s*5\s*years\b",
    r"\bat\s*least\s*5\s*years\b",
]


def requires_five_plus_years(title: str, description: str) -> bool:
    """Check if job requires 5+ years of experience (unless intern/co-op/student)."""
    t_lower = (title or "").lower()
    if any(skw in t_lower for skw in ALLOWED_STUDENT_KWS):
        return False

    full_text = f"{title} {description}".lower()
    for pattern in EXP_EXCLUSION_PATTERNS:
        if re.search(pattern, full_text):
            return True
    return False


def is_senior_role(title: str) -> bool:
    """Check if a title is a Senior/Lead/Manager role (unless student/intern)."""
    t_lower = title.lower()
    
    # If it explicitly mentions intern/co-op/student, allow it
    if any(skw in t_lower for skw in ALLOWED_STUDENT_KWS):
        return False

    # Check for senior exclusions
    for ex in SENIOR_EXCLUSIONS:
        if ex in t_lower:
            return True
    return False


def strip_html(raw_text: str) -> str:
    """Completely strip all HTML tags and unescape entities."""
    if not raw_text:
        return ""

    text = html.unescape(raw_text)
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_all_jobs():
    """Sanitize all jobs in SQLite database."""
    conn = database.get_connection()
    jobs = conn.execute(
        "SELECT id, title, company, location, description, apply_url FROM jobs"
    ).fetchall()

    updated = 0
    deleted_invalid = 0

    for j in jobs:
        job_id = j["id"]
        title_raw = j["title"]
        company_raw = j["company"]
        location_raw = j["location"]
        desc_raw = j["description"]
        apply_url_raw = j["apply_url"]

        title = strip_html(title_raw)
        company = strip_html(company_raw)
        location = strip_html(location_raw)
        description = strip_html(desc_raw)

        # 1. Filter out Senior / Lead roles or 5+ Years Experience
        if is_senior_role(title) or requires_five_plus_years(title, description):
            conn.execute("DELETE FROM chance_scores WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM job_analysis WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            deleted_invalid += 1
            continue

        if company == "↳" or not company:
            company = "Top Tech Company"

        match = re.search(r"https?://[^\s<>\"\']+", apply_url_raw or "")
        apply_url = match.group(0).rstrip('">\'') if match else ""

        if not apply_url or not title:
            conn.execute("DELETE FROM chance_scores WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM job_analysis WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            deleted_invalid += 1
            continue

        conn.execute(
            """UPDATE jobs SET title = ?, company = ?, location = ?, description = ?, apply_url = ?
               WHERE id = ?""",
            (title, company, location, description, apply_url, job_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"✅ Cleaned {updated} jobs. Purged {deleted_invalid} Senior/Lead/corrupted roles.")


if __name__ == "__main__":
    sanitize_all_jobs()
