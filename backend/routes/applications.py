"""
Employmentmaxxing — Applications API Routes
Endpoints to manage application tracking pipeline (Kanban board).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import database

router = APIRouter(prefix="/api/applications", tags=["Applications"])


class CreateApplicationSchema(BaseModel):
    job_id: str
    status: str = "interested"  # interested | applied | screening | interview | offer | rejected
    notes: str = ""


class UpdateApplicationSchema(BaseModel):
    status: str | None = None
    notes: str | None = None
    applied_date: str | None = None
    follow_up_date: str | None = None
    response_received: bool | None = None


@router.get("")
def list_applications(status: str | None = None):
    """List tracked applications, optionally filtered by column status."""
    return database.get_applications(status=status)


@router.post("")
def create_application(data: CreateApplicationSchema):
    """Add a job to the application tracker board."""
    job = database.get_job_by_id(data.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    app_id = database.add_application(data.job_id, status=data.status)
    if data.notes:
        database.update_application(app_id, {"notes": data.notes})

    return {"status": "success", "id": app_id}


@router.patch("/{app_id}")
def update_application(app_id: int, updates: UpdateApplicationSchema):
    """Update an application (move columns, update notes, set applied date)."""
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    database.update_application(app_id, update_data)
    return {"status": "success", "id": app_id}


@router.delete("/{app_id}")
def delete_application(app_id: int):
    """Remove a job from the application tracker."""
    database.delete_application(app_id)
    return {"status": "success", "id": app_id}
