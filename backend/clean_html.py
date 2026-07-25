"""
Employmentmaxxing — Thorough HTML & Formatting Sanitizer
Strips raw HTML tags, unescapes entities, and cleans titles, companies, locations, and descriptions.
"""

import re
import html
from bs4 import BeautifulSoup
import database


def strip_html(raw_text: str) -> str:
    """Completely strip all HTML tags and unescape entities."""
    if not raw_text:
        return ""

    # Unescape HTML entities first (&amp;, &lt;, &gt;, &quot;, &apos;, &#39;, etc.)
    text = html.unescape(raw_text)

    # Use BeautifulSoup to parse away tags
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ", strip=True)

    # Remove extra spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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

        # Clean text fields
        title = strip_html(title_raw)
        company = strip_html(company_raw)
        location = strip_html(location_raw)
        description = strip_html(desc_raw)

        # Fix company artifacts like "↳" or empty names
        if company == "↳" or not company:
            company = "Top Tech Company"

        # Ensure valid URL
        match = re.search(r"https?://[^\s<>\"\']+", apply_url_raw or "")
        apply_url = match.group(0).rstrip('">\'') if match else ""

        if not apply_url or not title:
            # Delete corrupted rows without valid URL or title
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
    print(f"✅ Cleaned {updated} jobs. Removed {deleted_invalid} corrupted/invalid listings.")


if __name__ == "__main__":
    sanitize_all_jobs()
