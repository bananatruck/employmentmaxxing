"""
Employmentmaxxing — Date Normalizer Utility
Converts relative date strings ("2 days ago", "posted 1d ago", "3 hours ago")
and raw strings into standardized YYYY-MM-DD ISO timestamps.
"""

import re
from datetime import datetime, timedelta


def normalize_posted_date(date_str: str | None, default_date: str = None) -> str:
    """
    Convert relative or raw date string into YYYY-MM-DD ISO format.
    Examples:
        '2 days ago' -> '2026-07-23'
        '1d ago' -> '2026-07-24'
        '3 hours ago' -> '2026-07-25'
        'Just posted' -> '2026-07-25'
        '2026-07-20T14:30:00Z' -> '2026-07-20'
    """
    now = datetime.now()

    if not default_date:
        default_date = now.strftime("%Y-%m-%d")

    if not date_str:
        return default_date

    raw = str(date_str).strip().lower()

    if not raw or raw in ["null", "none", "unknown", "n/a"]:
        return default_date

    # Match YYYY-MM-DD directly
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if iso_match:
        return iso_match.group(1)

    # Match relative days: "2 days ago", "2d ago", "posted 3 days ago"
    days_match = re.search(r"(\d+)\s*(d|day|days)\s*ago?", raw)
    if days_match:
        days = int(days_match.group(1))
        return (now - timedelta(days=days)).strftime("%Y-%m-%d")

    # Match relative hours: "3 hours ago", "5h ago"
    hours_match = re.search(r"(\d+)\s*(h|hr|hrs|hour|hours)\s*ago?", raw)
    if hours_match:
        hours = int(hours_match.group(1))
        return (now - timedelta(hours=hours)).strftime("%Y-%m-%d")

    # Match relative weeks: "1 week ago", "2w ago"
    weeks_match = re.search(r"(\d+)\s*(w|wk|wks|week|weeks)\s*ago?", raw)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return (now - timedelta(weeks=weeks)).strftime("%Y-%m-%d")

    # Match "yesterday", "today", "just posted"
    if "yesterday" in raw:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in raw or "just" in raw or "hour" in raw or "min" in raw:
        return now.strftime("%Y-%m-%d")

    return default_date
