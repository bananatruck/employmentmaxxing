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
    scrape_interval_hours: int = 3  # Run every N hours
    scrape_max_results_per_query: int = 300
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
        "applied science intern"
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
        "SimplifyJobs/Summer2026-Internships",
    ]

    # ── Frontend ──────────────────────────────────────────────────────
    frontend_dir: str = str(PROJECT_ROOT / "frontend")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
