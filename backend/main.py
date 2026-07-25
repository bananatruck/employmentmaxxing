"""
Employmentmaxxing — Main Server Entry Point
FastAPI application serving API endpoints and frontend SPA assets.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings
from database import init_db, get_profile
from scheduler import start_scheduler, stop_scheduler
from routes import jobs, profile, applications, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print("🚀 Starting Employmentmaxxing Server...")

    # 1. Initialize Database Schema & Default Profile
    init_db()

    # 2. Ensure initial profile is loaded from CV if missing
    profile_data = get_profile()

    # 3. Start Background Scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    print("👋 Employmentmaxxing Server stopped.")


app = FastAPI(
    title=settings.app_name,
    description="Free, self-hosted AI job tracker for CS students targeting AI/ML/SWE/Quantum roles.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(analytics.router)

# Mount Frontend Static Assets
frontend_path = Path(settings.frontend_dir)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/")
def read_root():
    """Serve main frontend SPA dashboard."""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({
        "app": settings.app_name,
        "status": "backend running",
        "message": "Frontend index.html under construction"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
