"""
Employmentmaxxing — Workday ATS Provider Adapter
Queries public Workday CXS endpoints with pagination, repeat page protection,
relative date parsing, and title/location pre-filtering.
"""

import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

# pyrefly: ignore [missing-import]
import httpx
from clean_html import strip_html, is_senior_role
from config import settings
from scrapers.adapters.base import ATSJob, BaseATSAdapter
from scrapers.jobspy_scraper import is_remote

IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")

TARGET_KEYWORDS = [
    "intern", "internship", "co-op", "coop", "student", "university",
    "new grad", "entry", "junior", "early career",
    "machine learning", "ai ", "software", "deep learning", "nlp",
    "computer vision", "quantum", "data science", "mlops", "backend", "frontend",
    "full stack", "infrastructure", "systems", "platform", "cloud", "developer",
    "engineer", "researcher", "analyst", "scientist"
]


def parse_workday_url(url: str) -> dict[str, str] | None:
    """
    Parse canonical Workday URLs shaped like:
    https://{tenant}.{instance}.myworkdayjobs.com/{site}
    or https://{tenant}.{instance}.myworkdayjobs.com/en-US/{site}
    """
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        netloc_parts = parsed.netloc.lower().split(".")
        if len(netloc_parts) < 3 or "myworkdayjobs" not in netloc_parts[-2]:
            return None

        tenant = netloc_parts[0]
        instance = ".".join(netloc_parts[1:-2]) if len(netloc_parts) > 3 else netloc_parts[1]

        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if not path_parts:
            return None

        site = path_parts[-1]
        # Ignore language prefixes like en-US
        if len(path_parts) > 1 and path_parts[0].lower() not in ("en-us", "en_us", "en"):
            site = path_parts[0]

        if not (IDENTIFIER_REGEX.match(tenant) and IDENTIFIER_REGEX.match(site)):
            return None

        return {
            "tenant": tenant,
            "instance": instance,
            "site": site,
            "canonical_url": f"https://{tenant}.{instance}.myworkdayjobs.com/{site}",
        }
    except Exception:
        return None


def parse_workday_relative_date(posted_str: str) -> str:
    """Parse relative posting dates into standardized YYYY-MM-DD ISO string."""
    if not posted_str:
        return datetime.now().strftime("%Y-%m-%d")
    s = posted_str.lower()
    now = datetime.now()
    if "today" in s:
        return now.strftime("%Y-%m-%d")
    if "yesterday" in s:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")

    m_day = re.search(r"(\d+)\+?\s+day", s)
    if m_day:
        return (now - timedelta(days=int(m_day.group(1)))).strftime("%Y-%m-%d")

    m_wk = re.search(r"(\d+)\+?\s+week", s)
    if m_wk:
        return (now - timedelta(weeks=int(m_wk.group(1)))).strftime("%Y-%m-%d")

    m_mo = re.search(r"(\d+)\+?\s+month", s)
    if m_mo:
        return (now - timedelta(days=int(m_mo.group(1)) * 30)).strftime("%Y-%m-%d")

    return now.strftime("%Y-%m-%d")


class WorkdayAdapter(BaseATSAdapter):
    """Adapter for Workday CXS job endpoints."""

    @property
    def provider_name(self) -> str:
        return "workday"

    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        tenant = board_meta.get("tenant")
        instance = board_meta.get("instance")
        site = board_meta.get("site")

        if not (tenant and instance and site):
            parsed = parse_workday_url(board_meta.get("canonical_url", ""))
            if not parsed:
                return []
            tenant = parsed["tenant"]
            instance = parsed["instance"]
            site = parsed["site"]

        company_name = board_meta.get("company_name") or tenant.replace("-", " ").title()
        board_key = f"{tenant}_{site}"

        jobs_endpoint = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

        max_pages = getattr(settings, "ats_workday_max_pages", 15)
        max_jobs = getattr(settings, "ats_workday_max_jobs", 300)
        limit = 20

        seen_external_ids: set[str] = set()
        jobs: list[ATSJob] = []

        offset = 0
        total_reported = None

        for page in range(max_pages):
            if len(jobs) >= max_jobs:
                break

            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }

            try:
                resp = await client.post(jobs_endpoint, json=payload, timeout=12.0)
                if resp.status_code != 200:
                    break

                data = resp.json()
                if not isinstance(data, dict):
                    break

                if total_reported is None:
                    total_reported = data.get("total", 0)

                postings = data.get("jobPostings", [])
                if not isinstance(postings, list) or not postings:
                    break

                page_new_ids = 0

                for item in postings:
                    if not isinstance(item, dict):
                        continue

                    title = strip_html(item.get("title", ""))
                    external_path = item.get("externalPath", "")
                    if not title or not external_path:
                        continue

                    # Generate external ID from path
                    ext_id = external_path.strip("/").split("/")[-1]
                    if ext_id in seen_external_ids:
                        continue

                    seen_external_ids.add(ext_id)
                    page_new_ids += 1

                    # Title pre-filter to eliminate senior roles or completely irrelevant titles
                    if is_senior_role(title):
                        continue
                    if not any(kw in title.lower() for kw in TARGET_KEYWORDS):
                        continue

                    location_name = strip_html(item.get("location", "US / Remote") or "US / Remote")
                    posted_raw = item.get("postedOn", "")
                    posted_iso = parse_workday_relative_date(posted_raw)

                    detail_url = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{external_path}"
                    apply_url = f"https://{tenant}.{instance}.myworkdayjobs.com/{site}{external_path}"

                    # Detail hydration
                    description = f"Workday posting at {company_name}: {title}."

                    try:
                        detail_resp = await client.get(detail_url, timeout=8.0)
                        if detail_resp.status_code == 200:
                            detail_data = detail_resp.json()
                            if isinstance(detail_data, dict):
                                job_info = detail_data.get("jobPostingInfo", {})
                                if isinstance(job_info, dict):
                                    desc_raw = job_info.get("jobDescription", "")
                                    if desc_raw:
                                        description = strip_html(desc_raw)
                                    if job_info.get("externalUrl"):
                                        apply_url = job_info.get("externalUrl")
                    except Exception:
                        pass

                    job = ATSJob(
                        provider="workday",
                        board_key=board_key,
                        external_job_id=ext_id,
                        title=title,
                        company=company_name,
                        location=location_name,
                        description=description,
                        apply_url=apply_url,
                        posted_at=posted_iso,
                        is_remote=is_remote(title, location_name, description),
                        raw_data={
                            "tenant": tenant,
                            "instance": instance,
                            "site": site,
                            "external_path": external_path,
                            "posted_on_raw": posted_raw,
                        },
                    )
                    jobs.append(job)

                # Termination safeguards:
                # 1. Page returned no new IDs (repeating loop)
                # 2. Page size smaller than limit
                # 3. Reached reported total
                if page_new_ids == 0 or len(postings) < limit:
                    break

                offset += limit
                if total_reported and offset >= total_reported:
                    break

            except (httpx.HTTPError, ValueError, Exception):
                break

        return jobs
