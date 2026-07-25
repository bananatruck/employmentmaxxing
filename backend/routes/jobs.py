"""
Employmentmaxxing — Jobs API Routes
Endpoints to list, filter, search, and detail job postings.
"""

import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import database

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("")
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    job_type: str | None = None,
    min_score: int | None = None,
    source: str | None = None,
    search: str | None = None,
    sort_by: str = Query("date_scraped", enum=["date_scraped", "date_posted", "company", "title", "overall_score"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
):
    """List jobs with pagination, filtering, search, and sorting."""
    jobs = database.get_jobs(
        limit=limit,
        offset=offset,
        job_type=job_type,
        min_score=min_score,
        source=source,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = database.get_job_count(job_type=job_type)

    # Clean up JSON fields for API response
    for j in jobs:
        if isinstance(j.get("all_sources"), str):
            try:
                j["all_sources"] = json.loads(j["all_sources"])
            except (json.JSONDecodeError, TypeError):
                j["all_sources"] = [j.get("source")]

    return {
        "total": total,
        "count": len(jobs),
        "offset": offset,
        "limit": limit,
        "jobs": jobs,
    }


@router.get("/{job_id}")
def get_job_detail(job_id: str):
    """Get complete job details, including AI analysis and chance score."""
    job = database.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Parse JSON fields
    json_fields = [
        "all_sources", "required_skills", "preferred_skills", "tech_stack",
        "red_flags", "green_flags", "improvement_tips"
    ]
    for field in json_fields:
        if isinstance(job.get(field), str):
            try:
                job[field] = json.loads(job[field])
            except (json.JSONDecodeError, TypeError):
                job[field] = []

    return job
