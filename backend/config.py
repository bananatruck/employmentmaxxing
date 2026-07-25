"""
Employmentmaxxing — Configuration
Central settings loaded from environment / .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

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
    scrape_interval_hours: int = 4  # Run every N hours
    scrape_max_results_per_query: int = 25
    scrape_delay_seconds: float = 2.0  # Delay between queries (rate limiting)

    # ── Search Queries ────────────────────────────────────────────────
    # Rotated through during each scrape cycle
    search_queries: list[str] = [
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
    ]

    # ── Target Locations ──────────────────────────────────────────────
    search_locations: list[str] = [
        "United States",
    ]

    # ── GitHub Repos to Monitor ───────────────────────────────────────
    github_repos: list[str] = [
        "speedyapply/2027-AI-College-Jobs",
        "speedyapply/2027-SWE-College-Jobs",
        "vanshb03/Summer2027-Internships",
    ]

    # ── Frontend ──────────────────────────────────────────────────────
    frontend_dir: str = str(PROJECT_ROOT / "frontend")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
