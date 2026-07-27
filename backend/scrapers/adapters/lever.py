"""
Employmentmaxxing — Lever ATS Provider Adapter
Queries official Lever public API endpoint and normalizes postings.
"""

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from clean_html import strip_html
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
ALLOWED_HOSTS = {"api.lever.co", "jobs.lever.co"}


def validate_lever_slug(slug: str) -> bool:
    """Ensure slug contains valid alphanumeric, hyphen, and underscore characters."""
    return bool(slug and SLUG_REGEX.match(slug))


def is_approved_lever_host(url: str) -> bool:
    """Verify URL targets approved Lever domains."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() in ALLOWED_HOSTS
    except Exception:
        return False


class LeverAdapter(BaseATSAdapter):
    """Adapter for Lever job boards."""

    @property
    def provider_name(self) -> str:
        return "lever"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        company_slug = board_meta.get("board_token") or board_meta.get("board_key")
        if not company_slug or not validate_lever_slug(company_slug):
            return []

        company_name = board_meta.get("company_name") or company_slug.replace("-", " ").title()
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

        try:
            resp = await client.get(url, follow_redirects=True, timeout=12.0)
            if resp.status_code != 200:
                return []

            raw_jobs = resp.json()
            if not isinstance(raw_jobs, list):
                return []

            jobs: list[ATSJob] = []

            for j in raw_jobs:
                if not isinstance(j, dict):
                    continue

                job_id = str(j.get("id", ""))
                title = strip_html(str(j.get("text", "")))
                if not job_id or not title:
                    continue

                categories = j.get("categories", {})
                if isinstance(categories, dict):
                    location_name = strip_html(categories.get("location", "US / Remote") or "US / Remote")
                    team = categories.get("team", "")
                    commitment = categories.get("commitment", "")
                else:
                    location_name = "US / Remote"
                    team, commitment = "", ""

                desc_plain = strip_html(str(j.get("descriptionPlain", "")))
                apply_url = str(j.get("applyUrl") or j.get("hostedUrl") or f"https://jobs.lever.co/{company_slug}/{job_id}")

                if not is_approved_lever_host(apply_url):
                    apply_url = f"https://jobs.lever.co/{company_slug}/{job_id}"

                created_at_ms = j.get("createdAt")
                posted_iso = None
                if created_at_ms and isinstance(created_at_ms, (int, float)):
                    try:
                        posted_iso = datetime.fromtimestamp(created_at_ms / 1000.0).strftime("%Y-%m-%d")
                    except Exception:
                        pass

                job = ATSJob(
                    provider="lever",
                    board_key=company_slug,
                    external_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_name,
                    description=desc_plain if desc_plain else f"Position at {company_name}: {title}.",
                    apply_url=apply_url,
                    posted_at=posted_iso,
                    is_remote=is_remote(title, location_name, desc_plain),
                    raw_data={
                        "company_slug": company_slug,
                        "team": team,
                        "commitment": commitment,
                        "created_at": created_at_ms,
                    },
                )
                jobs.append(job)

            return jobs

        except (httpx.HTTPError, ValueError, Exception):
            return []
