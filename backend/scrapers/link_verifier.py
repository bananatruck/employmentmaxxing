"""
Employmentmaxxing — Link Verification Layer
Performs fast HTTP checks on apply_url links to verify they are active and not 404/expired.
"""

import httpx
import asyncio
import re
from database import get_connection

# Common error page indicators in response body/title
EXPIRED_INDICATORS = [
    "page you are looking for doesn't exist",
    "job no longer available",
    "position has been filled",
    "job is closed",
    "404 not found",
    "career site unavailable",
    "this posting has expired",
    "no longer accepting applications",
]


async def check_url_active(client: httpx.AsyncClient, url: str) -> bool:
    """Check if an apply URL is active and returning a valid job page."""
    if not url or not url.startswith("http"):
        return False

    try:
        # Try HEAD request first for speed
        resp = await client.head(url, follow_redirects=True, timeout=5.0)
        if resp.status_code == 404 or resp.status_code >= 500:
            return False

        if resp.status_code == 200:
            return True

        # Fall back to GET request if HEAD is not supported by target domain
        resp_get = await client.get(url, follow_redirects=True, timeout=5.0)
        if resp_get.status_code == 404 or resp_get.status_code >= 500:
            return False

        # Check response body for dead job keywords
        text_lower = resp_get.text.lower()
        for kw in EXPIRED_INDICATORS:
            if kw in text_lower:
                return False

        return True

    except Exception:
        # If connection fails completely, mark inactive
        return False


async def verify_database_links_async(limit: int = 100) -> dict:
    """Verify active status of unverified job links in database."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, apply_url FROM jobs WHERE is_active = TRUE ORDER BY date_scraped DESC LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        conn.close()
        return {"verified": 0, "deactivated": 0}

    deactivated = 0
    verified = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        tasks = [check_url_active(client, r["apply_url"]) for r in rows]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for row, is_active in zip(rows, results):
            job_id = row["id"]
            if is_active is True:
                verified += 1
            else:
                # Mark expired link as inactive
                conn.execute("UPDATE jobs SET is_active = FALSE WHERE id = ?", (job_id,))
                deactivated += 1

    conn.commit()
    conn.close()
    print(f"🔗 Link Verification Complete: {verified} active links verified, {deactivated} dead/404 links deactivated.")
    return {"verified": verified, "deactivated": deactivated}


def verify_database_links(limit: int = 100) -> dict:
    """Sync wrapper for link verification."""
    try:
        return asyncio.run(verify_database_links_async(limit=limit))
    except Exception as e:
        print(f"⚠️ Link verification error: {e}")
        return {"verified": 0, "deactivated": 0}


if __name__ == "__main__":
    verify_database_links(limit=500)
