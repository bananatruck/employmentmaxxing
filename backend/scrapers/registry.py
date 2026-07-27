"""
Employmentmaxxing — ATS Registry & Discovery Engine
Seeds, caches, validates, and discovers global Greenhouse and Workday ATS boards.
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config import settings
from database import upsert_ats_board, get_ats_boards
from scrapers.adapters.greenhouse import validate_greenhouse_token, is_approved_host as is_greenhouse_approved_host
from scrapers.adapters.workday import parse_workday_url
from scrapers.adapters.lever import validate_lever_slug
from scrapers.adapters.ashby import validate_ashby_slug
from scrapers.adapters.smartrecruiters import validate_smartrecruiters_slug
from scrapers.adapters.bamboohr import validate_bamboohr_slug
from scrapers.company_ats_scraper import GREENHOUSE_COMPANIES, LEVER_COMPANIES

DATA_DIR = Path(getattr(settings, "data_dir", Path(__file__).resolve().parent.parent / "data"))
CACHE_FILE = Path(getattr(settings, "ats_cache_file", DATA_DIR / "external_boards_cache.json"))
OVERRIDES_FILE = Path(getattr(settings, "ats_overrides_file", DATA_DIR / "ats_overrides.json"))


WORKDAY_DEFAULT_BOARDS = [
    {
        "canonical_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "company_name": "NVIDIA",
    },
    {
        "canonical_url": "https://snowflake.wd1.myworkdayjobs.com/Snowflake_Careers",
        "company_name": "Snowflake",
    },
    {
        "canonical_url": "https://adobe.wd5.myworkdayjobs.com/external_experienced",
        "company_name": "Adobe",
    },
    {
        "canonical_url": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site",
        "company_name": "Salesforce",
    },
]

ASHBY_DEFAULT_SLUGS = [
    "openai", "notion", "ramp", "linear", "sentry", "resend", "clerk", "postman", "vllm"
]

SMARTRECRUITERS_DEFAULT_SLUGS = [
    "square", "block", "visa", "bosch", "ubisoft", "spotify"
]

BAMBOOHR_DEFAULT_SLUGS = [
    "postman", "sourcegraph"
]


def discover_board_from_url(raw_url: str, company_name: str = "", source: str = "url_scraper") -> dict[str, Any] | None:
    """
    Parse an arbitrary ATS URL, validate it against host and character rules,
    and register it into SQLite database if valid.
    """
    if not raw_url:
        return None

    url = raw_url.strip()
    url_lower = url.lower()

    # 1. Greenhouse URL check
    if "greenhouse.io" in url_lower:
        try:
            parsed = urlparse(url)
            if not is_greenhouse_approved_host(url):
                return None
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            token = None
            if "boards" in path_parts and len(path_parts) >= 2:
                idx = path_parts.index("boards")
                if idx + 1 < len(path_parts):
                    token = path_parts[idx + 1]
            elif path_parts:
                token = path_parts[0]

            if token and validate_greenhouse_token(token):
                clean_name = company_name or token.replace("-", " ").title()
                board_data = {
                    "provider": "greenhouse",
                    "board_key": token,
                    "company_name": clean_name,
                    "board_token": token,
                    "canonical_url": f"https://boards.greenhouse.io/{token}",
                    "discovery_source": source,
                }
                upsert_ats_board(board_data)
                return board_data
        except Exception:
            pass

    # 2. Workday URL check
    if "myworkdayjobs.com" in url_lower:
        parsed_wd = parse_workday_url(url)
        if parsed_wd:
            tenant = parsed_wd["tenant"]
            instance = parsed_wd["instance"]
            site = parsed_wd["site"]
            board_key = f"{tenant}_{site}"
            clean_name = company_name or tenant.replace("-", " ").title()

            board_data = {
                "provider": "workday",
                "board_key": board_key,
                "company_name": clean_name,
                "tenant": tenant,
                "instance": instance,
                "site": site,
                "canonical_url": parsed_wd["canonical_url"],
                "discovery_source": source,
            }
            upsert_ats_board(board_data)
            return board_data

    # 3. Lever URL check
    if "lever.co" in url_lower:
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if path_parts:
                slug = path_parts[0]
                if validate_lever_slug(slug):
                    clean_name = company_name or slug.replace("-", " ").title()
                    board_data = {
                        "provider": "lever",
                        "board_key": slug,
                        "company_name": clean_name,
                        "board_token": slug,
                        "canonical_url": f"https://jobs.lever.co/{slug}",
                        "discovery_source": source,
                    }
                    upsert_ats_board(board_data)
                    return board_data
        except Exception:
            pass

    # 4. Ashby URL check
    if "ashbyhq.com" in url_lower:
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if path_parts:
                slug = path_parts[0]
                if validate_ashby_slug(slug):
                    clean_name = company_name or slug.replace("-", " ").title()
                    board_data = {
                        "provider": "ashby",
                        "board_key": slug,
                        "company_name": clean_name,
                        "board_token": slug,
                        "canonical_url": f"https://jobs.ashbyhq.com/{slug}",
                        "discovery_source": source,
                    }
                    upsert_ats_board(board_data)
                    return board_data
        except Exception:
            pass

    # 5. SmartRecruiters URL check
    if "smartrecruiters.com" in url_lower:
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if path_parts:
                slug = path_parts[0]
                if validate_smartrecruiters_slug(slug):
                    clean_name = company_name or slug.replace("-", " ").title()
                    board_data = {
                        "provider": "smartrecruiters",
                        "board_key": slug,
                        "company_name": clean_name,
                        "board_token": slug,
                        "canonical_url": f"https://jobs.smartrecruiters.com/{slug}",
                        "discovery_source": source,
                    }
                    upsert_ats_board(board_data)
                    return board_data
        except Exception:
            pass

    # 6. BambooHR URL check
    if "bamboohr.com" in url_lower:
        try:
            parsed = urlparse(url)
            host_parts = parsed.netloc.lower().split(".")
            if len(host_parts) >= 3 and "bamboohr" in host_parts[-2]:
                slug = host_parts[0]
                if validate_bamboohr_slug(slug):
                    clean_name = company_name or slug.replace("-", " ").title()
                    board_data = {
                        "provider": "bamboohr",
                        "board_key": slug,
                        "company_name": clean_name,
                        "board_token": slug,
                        "canonical_url": f"https://{slug}.bamboohr.com/careers",
                        "discovery_source": source,
                    }
                    upsert_ats_board(board_data)
                    return board_data
        except Exception:
            pass

    return None


def load_user_overrides() -> list[dict[str, Any]]:
    """Load user-maintained overrides from JSON file."""
    if not OVERRIDES_FILE.exists():
        return []
    try:
        with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            results = []
            if isinstance(data, dict):
                # Greenhouse overrides
                for item in data.get("greenhouse", []):
                    token = item.get("board_token") or item.get("board_key")
                    if token and validate_greenhouse_token(token):
                        results.append({
                            "provider": "greenhouse",
                            "board_key": token,
                            "company_name": item.get("company_name", token.replace("-", " ").title()),
                            "board_token": token,
                            "canonical_url": f"https://boards.greenhouse.io/{token}",
                            "discovery_source": "user_override",
                        })
                # Lever overrides
                for item in data.get("lever", []):
                    slug = item.get("board_token") or item.get("board_key")
                    if slug and validate_lever_slug(slug):
                        results.append({
                            "provider": "lever",
                            "board_key": slug,
                            "company_name": item.get("company_name", slug.replace("-", " ").title()),
                            "board_token": slug,
                            "canonical_url": f"https://jobs.lever.co/{slug}",
                            "discovery_source": "user_override",
                        })
                # Ashby overrides
                for item in data.get("ashby", []):
                    slug = item.get("board_token") or item.get("board_key")
                    if slug and validate_ashby_slug(slug):
                        results.append({
                            "provider": "ashby",
                            "board_key": slug,
                            "company_name": item.get("company_name", slug.replace("-", " ").title()),
                            "board_token": slug,
                            "canonical_url": f"https://jobs.ashbyhq.com/{slug}",
                            "discovery_source": "user_override",
                        })
                # Workday overrides
                for item in data.get("workday", []):
                    url = item.get("canonical_url", "")
                    parsed_wd = parse_workday_url(url)
                    if parsed_wd:
                        results.append({
                            "provider": "workday",
                            "board_key": f"{parsed_wd['tenant']}_{parsed_wd['site']}",
                            "company_name": item.get("company_name", parsed_wd["tenant"].replace("-", " ").title()),
                            "tenant": parsed_wd["tenant"],
                            "instance": parsed_wd["instance"],
                            "site": parsed_wd["site"],
                            "canonical_url": parsed_wd["canonical_url"],
                            "discovery_source": "user_override",
                        })
            return results
    except Exception as e:
        print(f"⚠️ Error loading ATS user overrides: {e}")
        return []


def seed_default_registry():
    """Seed database with default ATS boards across Greenhouse, Lever, Workday, Ashby, SmartRecruiters, BambooHR."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Greenhouse defaults
    for company in GREENHOUSE_COMPANIES:
        if validate_greenhouse_token(company):
            upsert_ats_board({
                "provider": "greenhouse",
                "board_key": company,
                "company_name": company.replace("-", " ").title(),
                "board_token": company,
                "canonical_url": f"https://boards.greenhouse.io/{company}",
                "discovery_source": "seed_default",
            })

    # 2. Lever defaults
    for company in LEVER_COMPANIES:
        if validate_lever_slug(company):
            upsert_ats_board({
                "provider": "lever",
                "board_key": company,
                "company_name": company.replace("-", " ").title(),
                "board_token": company,
                "canonical_url": f"https://jobs.lever.co/{company}",
                "discovery_source": "seed_default",
            })

    # 3. Workday defaults
    for item in WORKDAY_DEFAULT_BOARDS:
        discover_board_from_url(item["canonical_url"], company_name=item["company_name"], source="seed_default")

    # 4. Ashby defaults
    for slug in ASHBY_DEFAULT_SLUGS:
        if validate_ashby_slug(slug):
            upsert_ats_board({
                "provider": "ashby",
                "board_key": slug,
                "company_name": slug.replace("-", " ").title(),
                "board_token": slug,
                "canonical_url": f"https://jobs.ashbyhq.com/{slug}",
                "discovery_source": "seed_default",
            })

    # 5. SmartRecruiters defaults
    for slug in SMARTRECRUITERS_DEFAULT_SLUGS:
        if validate_smartrecruiters_slug(slug):
            upsert_ats_board({
                "provider": "smartrecruiters",
                "board_key": slug,
                "company_name": slug.replace("-", " ").title(),
                "board_token": slug,
                "canonical_url": f"https://jobs.smartrecruiters.com/{slug}",
                "discovery_source": "seed_default",
            })

    # 6. BambooHR defaults
    for slug in BAMBOOHR_DEFAULT_SLUGS:
        if validate_bamboohr_slug(slug):
            upsert_ats_board({
                "provider": "bamboohr",
                "board_key": slug,
                "company_name": slug.replace("-", " ").title(),
                "board_token": slug,
                "canonical_url": f"https://{slug}.bamboohr.com/careers",
                "discovery_source": "seed_default",
            })

    # 7. User overrides
    overrides = load_user_overrides()
    for board in overrides:
        upsert_ats_board(board)



def refresh_external_registry() -> dict[str, int]:
    """
    Refresh local ATS board registry.
    Retains previously discovered boards while seeding new ones.
    """
    seed_default_registry()
    boards = get_ats_boards()
    counts = {
        "total": len(boards),
        "greenhouse": 0,
        "workday": 0,
        "lever": 0,
        "ashby": 0,
        "smartrecruiters": 0,
        "bamboohr": 0,
    }
    for b in boards:
        p = b.get("provider")
        if p and p in counts:
            counts[p] += 1
        elif p:
            counts[p] = 1
    return counts
