"""
Employmentmaxxing — Jobs API Routes
Endpoints supporting Company Tier filtering (Top 10, Top 20, Top 50, Startups),
multi-category checkboxes, Released Date sorting, and 30-day freshness.
"""

import json
from fastapi import APIRouter, Query, HTTPException
import database

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

TOP_10_COMPANIES = ["openai", "anthropic", "google", "meta", "nvidia", "apple", "microsoft", "amazon", "stripe", "netflix"]
TOP_20_COMPANIES = TOP_10_COMPANIES + ["databricks", "snowflake", "palantir", "scale ai", "scaleai", "figma", "vercel", "coinbase", "airbnb", "datadog"]
TOP_50_COMPANIES = TOP_20_COMPANIES + ["cloudflare", "roblox", "pinterest", "discord", "duolingo", "plaid", "brex", "ramp", "notion", "retool", "linear", "gusto", "chime", "postman", "sentry", "supabase", "huggingface", "cohere", "mistral", "anysphere", "cursor", "perplexity", "modal", "elevenlabs", "together ai", "togetherai", "pinecone", "weaviate", "replit", "langchain"]


@router.get("")
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    company_tier: str | None = Query(None, description="top_10 | top_20 | top_50 | startups"),
    job_types: str | None = Query(None, description="Comma-separated categories: AI/ML,SWE,Quantum,Data Science"),
    experience_levels: str | None = Query(None, description="Comma-separated levels: intern,co-op,new_grad"),
    min_score: int | None = None,
    source: str | None = None,
    search: str | None = None,
    max_days_old: int = Query(30, description="Max posting age in days"),
    sort_by: str = Query("earliest_release", enum=["highest_match", "earliest_release", "date_scraped", "company"]),
):
    """List jobs with company tier filtering, multi-category checkboxes, and date sorting."""
    type_list = [t.strip() for t in job_types.split(",") if t.strip()] if job_types else None
    exp_list = [e.strip() for e in experience_levels.split(",") if e.strip()] if experience_levels else None

    # Retrieve candidate jobs
    jobs = database.get_jobs(
        limit=limit * 3 if company_tier else limit,
        offset=offset,
        job_types=type_list,
        experience_levels=exp_list,
        min_score=min_score,
        source=source,
        search=search,
        max_days_old=max_days_old,
        sort_by=sort_by,
    )

    # Filter by Company Tier if specified
    if company_tier == "top_10":
        jobs = [j for j in jobs if any(c in j["company"].lower() for c in TOP_10_COMPANIES)]
    elif company_tier == "top_20":
        jobs = [j for j in jobs if any(c in j["company"].lower() for c in TOP_20_COMPANIES)]
    elif company_tier == "top_50":
        jobs = [j for j in jobs if any(c in j["company"].lower() for c in TOP_50_COMPANIES)]
    elif company_tier == "startups":
        jobs = [j for j in jobs if j.get("source") in ["startup_official", "hn_whos_hiring"] or any(c in j["company"].lower() for c in TOP_50_COMPANIES[20:])]

    jobs = jobs[:limit]
    total = database.get_job_count(job_types=type_list)

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
    """Get complete job details."""
    job = database.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
