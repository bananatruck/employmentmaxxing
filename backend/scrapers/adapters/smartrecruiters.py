"""
Employmentmaxxing — SmartRecruiters ATS Provider Adapter
Queries official SmartRecruiters public posting API endpoint and normalizes postings.
"""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from clean_html import strip_html
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
ALLOWED_HOSTS = {"api.smartrecruiters.com", "jobs.smartrecruiters.com"}


def validate_smartrecruiters_slug(slug: str) -> bool:
    """Ensure slug contains valid alphanumeric, hyphen, and underscore characters."""
    return bool(slug and SLUG_REGEX.match(slug))


class SmartRecruitersAdapter(BaseATSAdapter):
    """Adapter for SmartRecruiters job boards."""

    @property
    def provider_name(self) -> str:
        return "smartrecruiters"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        company_slug = board_meta.get("board_token") or board_meta.get("board_key")
        if not company_slug or not validate_smartrecruiters_slug(company_slug):
            return []

        company_name = board_meta.get("company_name") or company_slug.replace("-", " ").title()
        url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings?limit=100"

        try:
            resp = await client.get(url, follow_redirects=True, timeout=12.0)
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not isinstance(data, dict):
                return []

            raw_jobs = data.get("content", [])
            if not isinstance(raw_jobs, list):
                return []

            jobs: list[ATSJob] = []

            for j in raw_jobs:
                if not isinstance(j, dict):
                    continue

                job_id = str(j.get("id", ""))
                title = strip_html(str(j.get("name", "")))
                if not job_id or not title:
                    continue

                loc_data = j.get("location", {})
                city = loc_data.get("city", "")
                region = loc_data.get("region", "")
                country = loc_data.get("country", "").upper()
                loc_parts = [p for p in [city, region, country] if p]
                location_name = ", ".join(loc_parts) if loc_parts else "US / Remote"
                is_remote_flag = bool(loc_data.get("remote", False)) or is_remote(title, location_name)

                apply_url = f"https://jobs.smartrecruiters.com/{company_slug}/{job_id}"
                pub_at = str(j.get("releasedDate", ""))[:10] if j.get("releasedDate") else None

                job = ATSJob(
                    provider="smartrecruiters",
                    board_key=company_slug,
                    external_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_name,
                    description=f"Official position at {company_name}: {title}.",
                    apply_url=apply_url,
                    posted_at=pub_at,
                    is_remote=is_remote_flag,
                    raw_data={
                        "company_slug": company_slug,
                        "refNumber": j.get("refNumber"),
                    },
                )
                jobs.append(job)

            return jobs

        except (httpx.HTTPError, ValueError, Exception):
            return []
