"""
Employmentmaxxing — Exclusion & Eligibility Filter Module
Filters out Defense/Military contractors (including Palantir) and US Citizenship / Security Clearance restricted job postings.
"""

import re

DEFENSE_BLACK_LIST = [
    "palantir", "lockheed martin", "lockheed", "northrop grumman", "northrop", "raytheon", "rtx",
    "general dynamics", "l3harris", "l3 harris", "bae systems", "booz allen hamilton",
    "booz allen", "leidos", "huntington ingalls", "caci", "saic", "aerojet rocketdyne",
    "anduril", "textron", "oshkosh defense", "kratos", "defense intelligence",
]

CLEARANCE_PATTERNS = [
    r"u\.?s\.?\s*citizenship\s*required",
    r"u\.?s\.?\s*citizen\b",
    r"must\s*be\s*a\s*u\.?s\.?\s*person",
    r"green\s*card\s*required",
    r"permanent\s*resident",
    r"active\s*secret\s*clearance",
    r"top\s*secret\s*/?\s*sci",
    r"top\s*secret\b",
    r"secret\s*clearance",
    r"itar\s*compliant",
    r"itar\s*restricted",
    r"security\s*clearance\s*required",
    r"dod\s*clearance",
]


def is_defense_contractor(company: str = "") -> bool:
    """Check if company is a defense/military contractor on the blacklist."""
    if not company:
        return False
    c_lower = company.lower().strip()
    for def_comp in DEFENSE_BLACK_LIST:
        if def_comp in c_lower:
            return True
    return False


def requires_citizenship_or_clearance(description: str = "", title: str = "") -> bool:
    """Scan job title and description text for US Citizenship or Security Clearance requirements."""
    full_text = f"{title} {description}".lower()

    for pattern in CLEARANCE_PATTERNS:
        if re.search(pattern, full_text):
            return True

    return False


def is_job_eligible(job_data: dict) -> tuple[bool, str]:
    """
    Check if a job is eligible.
    Returns (is_eligible, reason_if_excluded).
    """
    company = job_data.get("company", "")
    title = job_data.get("title", "")
    description = job_data.get("description", "")

    # Check defense contractor blacklist (including Palantir)
    if is_defense_contractor(company):
        return False, f"Defense contractor excluded ({company})"

    # Check clearance/citizenship restrictions
    if requires_citizenship_or_clearance(description, title):
        return False, "US Citizenship / Security Clearance restricted"

    return True, "Eligible"
