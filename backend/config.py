"""
Employmentmaxxing — Configuration
Central settings loaded from environment / .env files.
"""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from .env or environment variables."""

    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Employmentmaxxing"
    debug: bool = True

    # ── Database ──────────────────────────────────────────────────────
    db_path: str = str(BASE_DIR / "employmentmaxxing.db")

    # ── Gemini AI ─────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"  # Free-tier Flash model

    # ── Scraping Schedule ─────────────────────────────────────────────
    scrape_interval_hours: int = 3  # Run every N hours
    scrape_max_results_per_query: int = 300
    scrape_delay_seconds: float = 2.0  # Delay between queries (rate limiting)

    # ── Search Queries ────────────────────────────────────────────────
    search_queries: List[str] = Field(
        default_factory=lambda: [
            "AI ML intern",
            "machine learning internship",
            "software engineer intern",
            "software engineering co-op",
            "AI research intern",
            "deep learning internship",
            "quantum computing intern",
            "computer science intern 2027",
            "NLP intern",
            "computer vision intern",
            "data science intern",
            "MLOps intern",
            "software engineer",
            "software development engineer",
            "backend engineer",
            "frontend engineer",
            "full stack engineer",
            "data engineer",
            "data analyst",
            "machine learning engineer",
            "AI engineer",
            "computer vision engineer",
            "NLP engineer",
            "AI/ML intern",
            "backend engineer intern",
            "frontend engineer intern",
            "full stack engineer intern",
            "data engineer intern",
            "data analyst intern",
            "machine learning engineer intern",
            "AI engineer intern",
            "computer vision engineer intern",
            "NLP engineer intern",
            "AI/ML engineer",
            "research intern",
            "R&D intern",
            "applied science intern",
        ]
    )

    # ── Target Locations ──────────────────────────────────────────────
    search_locations: List[str] = Field(
        default_factory=lambda: ["United States"]
    )

    # ── GitHub Repos to Monitor ───────────────────────────────────────
    github_repos: List[str] = Field(
        default_factory=lambda: [
            "speedyapply/2027-AI-College-Jobs",
            "speedyapply/2027-SWE-College-Jobs",
            "vanshb03/Summer2027-Internships",
            "SimplifyJobs/Summer2027-Internships",
            "SimplifyJobs/Summer2026-Internships",
            "SimplifyJobs/New-Grad-Positions",
        ]
    )

    # ── Frontend & Data Paths ──────────────────────────────────────────
    frontend_dir: str = str(PROJECT_ROOT / "frontend")
    data_dir: str = str(BASE_DIR / "data")
    ats_cache_file: str = str(BASE_DIR / "data" / "external_boards_cache.json")
    ats_overrides_file: str = str(BASE_DIR / "data" / "ats_overrides.json")

    # ── ATS Discovery & Crawler Settings ──────────────────────────────
    ats_concurrency_limit: int = 15
    ats_per_host_concurrency: int = 3
    ats_request_delay_seconds: float = 0.5
    ats_max_retries: int = 3
    ats_workday_max_pages: int = 15
    ats_workday_max_jobs: int = 300
    ats_enabled_providers: List[str] = Field(
        default_factory=lambda: ["greenhouse", "workday"]
    )
    ats_registry_refresh_hours: int = 24
    ats_global_scan_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), str(PROJECT_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

