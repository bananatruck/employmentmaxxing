"""
Employmentmaxxing — BambooHR ATS Provider Adapter
Queries official BambooHR public career list API endpoint and normalizes postings.
"""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from clean_html import strip_html
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_bamboohr_slug(slug: str) -> bool:
    """Ensure slug contains valid alphanumeric, hyphen, and underscore characters."""
    return bool(slug and SLUG_REGEX.match(slug))


class BambooHRAdapter(BaseATSAdapter):
    """Adapter for BambooHR job boards."""

    @property
    def provider_name(self) -> str:
        return "bamboohr"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        company_slug = board_meta.get("board_token") or board_meta.get("board_key")
        if not company_slug or not validate_bamboohr_slug(company_slug):
            return []

        company_name = board_meta.get("company_name") or company_slug.replace("-", " ").title()
        url = f"https://{company_slug}.bamboohr.com/careers/list"

        try:
            resp = await client.get(url, follow_redirects=True, timeout=12.0)
            if resp.status_code != 200:
                return []

            data = resp.json()
            raw_jobs = data.get("result", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

            jobs: list[ATSJob] = []

            for j in raw_jobs:
                if not isinstance(j, dict):
                    continue

                job_id = str(j.get("id", ""))
                title = strip_html(str(j.get("jobTitle", j.get("title", ""))))
                if not job_id or not title:
                    continue

                loc_data = j.get("location", {})
                if isinstance(loc_data, dict):
                    city = loc_data.get("city", "")
                    state = loc_data.get("state", "")
                    loc_parts = [p for p in [city, state] if p]
                    location_name = ", ".join(loc_parts) if loc_parts else "US / Remote"
                else:
                    location_name = strip_html(str(loc_data) or "US / Remote")

                apply_url = f"https://{company_slug}.bamboohr.com/careers/{job_id}"

                job = ATSJob(
                    provider="bamboohr",
                    board_key=company_slug,
                    external_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_name,
                    description=f"Position at {company_name}: {title}.",
                    apply_url=apply_url,
                    posted_at=None,
                    is_remote=is_remote(title, location_name),
                    raw_data={
                        "company_slug": company_slug,
                        "department": j.get("department"),
                    },
                )
                jobs.append(job)

            return jobs

        except (httpx.HTTPError, ValueError, Exception):
            return []
