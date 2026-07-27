"""
Employmentmaxxing — Profile API Routes
Endpoints to GET and POST user profile data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import database

router = APIRouter(prefix="/api/profile", tags=["Profile"])


class ProfileSchema(BaseModel):
    name: str = "Keshav Jindal"
    university: str = "California State University Long Beach"
    graduation_year: int = 2027
    degree: str = "BS Computer Science"
    gpa_range: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    open_to_remote: bool = True
    target_roles: list[str] = Field(default_factory=lambda: ["AI/ML", "SWE", "Quantum"])
    additional_context: str = ""


# Default profile populated from Keshav's CV
DEFAULT_KESHAV_PROFILE = {
    "name": "Keshav Jindal",
    "university": "California State University Long Beach",
    "graduation_year": 2027,
    "degree": "BS Computer Science",
    "gpa_range": "3.5-4.0",
    "skills": [
        "Python", "C++", "TypeScript", "JavaScript", "Go", "Rust", "Java", "C", "SQL", "HTML", "CSS",
        "PyTorch", "TensorFlow", "scikit-learn", "OpenCV", "NumPy", "Pandas",
        "React", "Next.js", "React Native", "FastAPI", "Flask", "Node.js",
        "Docker", "AWS", "PostgreSQL", "Redis", "Firebase", "Git", "GitHub Actions", "Terraform", "CI/CD", "Linux",
        "LLMs", "RAG", "Vector DBs", "Prompt Engineering", "Fine-tuning", "Computer Vision", "Multi-Agent Systems",
        "Time-Series Analysis", "REST APIs", "gRPC"
    ],
    "projects": [
        {
            "name": "DocWeave",
            "description": "Distributed Go crawler with PostgreSQL SKIP LOCKED leases processing 1,000 pages at 10 pages/sec with Prometheus/Grafana.",
            "tech_stack": ["Go", "PostgreSQL", "Docker", "Prometheus", "Grafana", "REST APIs"]
        },
        {
            "name": "Devflow Agent",
            "description": "Agentic developer tooling platform automating issue planning and workflow execution with FastAPI, PostgreSQL, Redis, Docker, GitHub Actions, React.",
            "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "GitHub Actions", "React"]
        },
        {
            "name": "Odysseus AI Workspace",
            "description": "Open source contributor to 73k+ star self-hosted AI workspace (fixed multi-line prompt & markdown search bug).",
            "tech_stack": ["Python", "Docker", "Linux", "LLMs"]
        },
        {
            "name": "Barter",
            "description": "Full-stack skill exchange platform with React, TypeScript, Flask, Firebase, WebSockets, OpenAI API, and AR navigation.",
            "tech_stack": ["React", "TypeScript", "Flask", "Firebase", "OpenAI API", "WebSockets"]
        },
        {
            "name": "FableFrog",
            "description": "Storyteller Speech-to-Speech AI chatbot using Python, React Native, OpenAI, Hugging Face, ElevenLabs, RAG, and PEFT fine-tuning.",
            "tech_stack": ["Python", "React Native", "OpenAI API", "Hugging Face", "RAG", "ElevenLabs"]
        }
    ],
    "preferred_locations": ["California", "United States", "Remote"],
    "open_to_remote": True,
    "target_roles": ["AI/ML", "SWE", "Quantum"],
    "additional_context": "CS student at CSULB graduating 2027. Founder & Project Lead at Project Starbound (30+ devs). BeachHacks Software Dev Lead (AWS, RAG, Fetch.ai). Published research contributor in AI time-series models."
}


@router.get("")
def get_user_profile():
    """Get the current profile. Populates default CV profile if empty."""
    profile = database.get_profile()

    # If profile has no skills set yet, populate from Keshav's CV
    if not profile or not profile.get("skills"):
        database.save_profile(DEFAULT_KESHAV_PROFILE)
        profile = database.get_profile()

    return profile


@router.post("")
def update_user_profile(profile: ProfileSchema):
    """Save/update the profile and trigger score recalculation."""
    data = profile.model_dump()
    database.save_profile(data)

    # Automatically re-score jobs with updated profile
    from analysis.chance_scorer import run_scoring_pipeline
    import threading
    threading.Thread(target=run_scoring_pipeline, kwargs={"limit": 300}, daemon=True).start()

    return {"status": "success", "message": "Profile updated. Background re-scoring started."}


@router.get("/resume")
def get_user_resume():
    """Get resume file information and preview URL."""
    from pathlib import Path
    static_file = Path(__file__).resolve().parent.parent / "static" / "Keshav_Jindal.pdf"
    exists = static_file.exists()
    return {
        "filename": "Keshav_Jindal.pdf",
        "exists": exists,
        "url": "/static/Keshav_Jindal.pdf",
        "size_bytes": static_file.stat().st_size if exists else 0,
        "title": "Keshav Jindal — Software Engineer & AI Researcher Resume"
    }
