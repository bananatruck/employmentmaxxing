"""
Employmentmaxxing — Database URL Sanitizer
Fixes any improperly formatted or HTML-wrapped apply_url entries in the SQLite database.
"""

import re
import database

from scrapers.link_verifier import is_generic_domain

def clean_database_urls():
    conn = database.get_connection()
    jobs = conn.execute("SELECT id, apply_url FROM jobs WHERE is_active = TRUE").fetchall()

    cleaned = 0
    deactivated = 0
    for row in jobs:
        job_id = row["id"]
        raw = row["apply_url"] or ""

        # Check if URL is generic homepage or root domain
        if is_generic_domain(raw):
            conn.execute("UPDATE jobs SET is_active = FALSE WHERE id = ?", (job_id,))
            deactivated += 1
            continue

        # Extract clean href URL
        match = re.search(r'https?://[^\s<>"\']+', raw)
        if match:
            clean = match.group(0).rstrip('">\'')
            if clean != raw:
                conn.execute("UPDATE jobs SET apply_url = ? WHERE id = ?", (clean, job_id))
                cleaned += 1

    conn.commit()
    conn.close()
    print(f"✅ Cleaned {cleaned} job apply URLs, deactivated {deactivated} generic domain URLs in database.")

if __name__ == "__main__":
    clean_database_urls()
