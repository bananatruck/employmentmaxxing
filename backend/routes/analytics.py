"""
Employmentmaxxing — Analytics API Routes
Endpoints to retrieve dashboard analytics.
"""

from fastapi import APIRouter
import database

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("")
def get_analytics():
    """Get aggregated analytics data (skill demand, score distribution, funnel, etc.)."""
    return database.get_analytics_stats()
