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
from scrapers.company_ats_scraper import GREENHOUSE_COMPANIES

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


def discover_board_from_url(raw_url: str, company_name: str = "", source: str = "url_scraper") -> dict[str, Any] | None:
    """
    Parse an arbitrary ATS URL, validate it against host and character rules,
    and register it into SQLite database if valid.
    """
    if not raw_url:
        return None

    url = raw_url.strip()

    # 1. Greenhouse URL check
    if "greenhouse.io" in url.lower():
        try:
            parsed = urlparse(url)
            if not is_greenhouse_approved_host(url):
                return None
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            token = None
            if "boards" in path_parts and len(path_parts) >= 2:
                # https://boards-api.greenhouse.io/v1/boards/{token}/jobs
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
    if "myworkdayjobs.com" in url.lower():
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
    """Seed database with default Greenhouse & Workday boards."""
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

    # 2. Workday defaults
    for item in WORKDAY_DEFAULT_BOARDS:
        discover_board_from_url(item["canonical_url"], company_name=item["company_name"], source="seed_default")

    # 3. User overrides
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
    counts = {"total": len(boards), "greenhouse": 0, "workday": 0}
    for b in boards:
        p = b.get("provider")
        if p in counts:
            counts[p] += 1
    return counts
