"""
Employmentmaxxing — Greenhouse ATS Provider Adapter
Queries official Greenhouse public board API endpoint and normalizes postings.
"""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from clean_html import strip_html
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

TOKEN_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
ALLOWED_HOSTS = {"boards-api.greenhouse.io", "boards.greenhouse.io", "job-boards.greenhouse.io"}


def validate_greenhouse_token(token: str) -> bool:
    """Ensure token contains only valid alphanumeric, hyphen, and underscore characters."""
    return bool(token and TOKEN_REGEX.match(token))


def is_approved_host(url: str) -> bool:
    """Verify URL targets approved Greenhouse domains."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() in ALLOWED_HOSTS
    except Exception:
        return False


class GreenhouseAdapter(BaseATSAdapter):
    """Adapter for Greenhouse job boards."""

    @property
    def provider_name(self) -> str:
        return "greenhouse"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        token = board_meta.get("board_token") or board_meta.get("board_key")
        if not token or not validate_greenhouse_token(token):
            return []

        company_name = board_meta.get("company_name") or token.replace("-", " ").title()
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        if not is_approved_host(url):
            return []

        try:
            resp = await client.get(url, follow_redirects=False)
            if resp.status_code != 200:
                return []

            # Safety check on final URL after redirects if any
            if resp.has_redirect_location and not is_approved_host(str(resp.headers.get("location", ""))):
                return []

            data = resp.json()
            if not isinstance(data, dict):
                return []

            # Optional org name from Greenhouse API
            org_name = data.get("name")
            if org_name and isinstance(org_name, str) and org_name.strip():
                company_name = org_name.strip()

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

                # Location handling
                location_obj = j.get("location", {})
                if isinstance(location_obj, dict):
                    location_name = strip_html(location_obj.get("name", "US / Remote") or "US / Remote")
                else:
                    location_name = strip_html(str(location_obj) or "US / Remote")

                content = strip_html(str(j.get("content", "")))
                apply_url = str(j.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{job_id}")

                # Reject external apply URLs that divert off Greenhouse
                if not is_approved_host(apply_url):
                    apply_url = f"https://boards.greenhouse.io/{token}/jobs/{job_id}"

                updated_at = str(j.get("updated_at", ""))[:10] if j.get("updated_at") else None

                departments = [d.get("name") for d in j.get("departments", []) if isinstance(d, dict) and d.get("name")]
                offices = [o.get("name") for o in j.get("offices", []) if isinstance(o, dict) and o.get("name")]
                language = str(j.get("language", ""))

                job = ATSJob(
                    provider="greenhouse",
                    board_key=token,
                    external_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_name,
                    description=content if content else f"Position at {company_name}: {title}.",
                    apply_url=apply_url,
                    updated_at=updated_at,
                    is_remote=is_remote(title, location_name, content),
                    raw_data={
                        "token": token,
                        "departments": departments,
                        "offices": offices,
                        "language": language,
                        "updated_at": j.get("updated_at"),
                    },
                )
                jobs.append(job)

            return jobs

        except (httpx.HTTPError, ValueError, Exception):
            return []
