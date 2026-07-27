"""
Employmentmaxxing — Scrape Control & ATS Status API Routes
Provides endpoints for triggering manual ATS scans and querying coverage telemetry.
"""

import asyncio
from typing import Any
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, status

import database
from database import is_ats_run_locked
from scrapers.ats_engine import run_ats_incremental_scan

router = APIRouter(prefix="/api/scrape", tags=["Scrape Controls"])


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_scrape(
    background_tasks: BackgroundTasks,
    providers: str | None = Query(None, description="Comma-separated list of providers to scan, e.g. greenhouse,workday"),
):
    """
    Trigger manual ATS incremental scan.
    Returns 409 Conflict if scan is already running.
    """
    lock_info = is_ats_run_locked()
    if lock_info.get("is_locked"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "already_running",
                "message": f"An ATS scrape task is already running (locked by {lock_info.get('locked_by')} since {lock_info.get('locked_at')}).",
            },
        )

    provider_list = [p.strip().lower() for p in providers.split(",") if p.strip()] if providers else ["greenhouse", "workday"]

    # Launch in background task
    background_tasks.add_task(run_ats_incremental_scan, providers=provider_list)

    return {
        "status": "accepted",
        "message": f"Triggered ATS incremental scan for providers: {', '.join(provider_list)}",
        "providers": provider_list,
    }


@router.get("/status")
def get_scrape_status() -> dict[str, Any]:
    """Retrieve complete coverage telemetry, active board counts, and crawl lock status."""
    coverage = database.get_ats_coverage_stats()
    return {
        "status": "ok",
        "run_lock": coverage.get("run_lock", {}),
        "is_running": coverage.get("run_lock", {}).get("is_locked", False),
        "boards_summary": {
            "total": coverage.get("boards_total", 0),
            "active": coverage.get("boards_active", 0),
            "failing": coverage.get("boards_failing", 0),
        },
        "jobs_summary": {
            "active_ats_jobs": coverage.get("active_ats_jobs", 0),
            "closed_ats_jobs": coverage.get("closed_ats_jobs", 0),
        },
        "by_provider": coverage.get("by_provider", {}),
        "last_complete_coverage_time": coverage.get("last_complete_coverage_time"),
    }
