"""
Employmentmaxxing — Analytics API Routes
Endpoints to retrieve dashboard analytics and trigger scrape cycles.
"""

from fastapi import APIRouter
import threading

import database
from config import settings

router = APIRouter(prefix="/api", tags=["Analytics & System"])


@router.get("/analytics")
def get_analytics():
    """Get aggregated analytics data (skill demand, score distribution, funnel, etc.)."""
    return database.get_analytics_stats()


@router.get("/scrape/status")
def get_scrape_status():
    """Check last scrape time, next scheduled run, and active configuration."""
    last_scrape = database.get_last_scrape()
    total_jobs = database.get_job_count()

    return {
        "last_scrape": last_scrape,
        "total_jobs": total_jobs,
        "scrape_interval_hours": settings.scrape_interval_hours,
        "configured_sources": ["JobSpy (5 boards)", "GitHub Community", "Quantum Boards", "Hacker News"],
        "target_queries": settings.search_queries,
    }


@router.post("/scrape/trigger")
def trigger_scrape():
    """Manually trigger a full scrape, analyze, and score cycle in the background."""
    from scheduler import run_full_pipeline

    thread = threading.Thread(target=run_full_pipeline, daemon=True)
    thread.start()

    return {
        "status": "triggered",
        "message": "Full scrape, analysis, and scoring pipeline started in background."
    }
