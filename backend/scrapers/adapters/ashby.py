"""
Employmentmaxxing — Ashby ATS Provider Adapter
Queries official Ashby public job-board API endpoint and normalizes postings.
"""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from clean_html import strip_html
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
ALLOWED_HOSTS = {"api.ashbyhq.com", "jobs.ashbyhq.com"}


def validate_ashby_slug(slug: str) -> bool:
    """Ensure slug contains valid alphanumeric, hyphen, and underscore characters."""
    return bool(slug and SLUG_REGEX.match(slug))


def is_approved_ashby_host(url: str) -> bool:
    """Verify URL targets approved Ashby domains."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() in ALLOWED_HOSTS
    except Exception:
        return False


class AshbyAdapter(BaseATSAdapter):
    """Adapter for Ashby job boards."""

    @property
    def provider_name(self) -> str:
        return "ashby"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        company_slug = board_meta.get("board_token") or board_meta.get("board_key")
        if not company_slug or not validate_ashby_slug(company_slug):
            return []

        company_name = board_meta.get("company_name") or company_slug.replace("-", " ").title()
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}?includeCompensation=true"

        try:
            resp = await client.get(url, follow_redirects=True, timeout=12.0)
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not isinstance(data, dict):
                return []

            raw_jobs = data.get("jobs", [])
            if not isinstance(raw_jobs, list):
                return []

            jobs: list[ATSJob] = []

            for j in raw_jobs:
                if not isinstance(j, dict):
                    continue

                job_id = str(j.get("id", ""))
                title = strip_html(str(j.get("title", "")))
                if not job_id or not title:
                    continue

                loc_val = j.get("location") or "US / Remote"
                if isinstance(loc_val, dict):
                    location_name = strip_html(loc_val.get("name", "US / Remote"))
                else:
                    location_name = strip_html(str(loc_val))

                is_remote_flag = bool(j.get("isRemote", False)) or is_remote(title, location_name)

                desc_html = j.get("descriptionHtml") or j.get("descriptionPlain") or ""
                desc = strip_html(str(desc_html))

                job_url = str(j.get("jobUrl") or j.get("applyUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{job_id}")

                if not is_approved_ashby_host(job_url):
                    job_url = f"https://jobs.ashbyhq.com/{company_slug}/{job_id}"

                pub_at = str(j.get("publishedAt", ""))[:10] if j.get("publishedAt") else None

                job = ATSJob(
                    provider="ashby",
                    board_key=company_slug,
                    external_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_name,
                    description=desc if desc else f"Position at {company_name}: {title}.",
                    apply_url=job_url,
                    posted_at=pub_at,
                    is_remote=is_remote_flag,
                    raw_data={
                        "company_slug": company_slug,
                        "department": j.get("department"),
                        "published_at": j.get("publishedAt"),
                    },
                )
                jobs.append(job)

            return jobs

        except (httpx.HTTPError, ValueError, Exception):
            return []
