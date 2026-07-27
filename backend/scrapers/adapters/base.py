"""
Employmentmaxxing — Base ATS Adapter Contract
Defines normalized ATSJob dataclass and abstract adapter interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
# pyrefly: ignore [missing-import]
import httpx


@dataclass
class ATSJob:
    """Normalized ATS Job listing contract across all providers."""
    provider: str
    board_key: str
    external_job_id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: str
    posted_at: str | None = None
    updated_at: str | None = None
    is_remote: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert normalized ATSJob to database job dict format."""
        from scrapers.jobspy_scraper import classify_job_type, detect_experience_level

        exp_level = detect_experience_level(self.title, self.description)
        j_type = classify_job_type(self.title, self.description)

        return {
            "ats_provider": self.provider,
            "ats_board_key": self.board_key,
            "ats_job_id": self.external_job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "is_remote": self.is_remote,
            "description": self.description,
            "apply_url": self.apply_url,
            "date_posted": self.posted_at or self.updated_at,
            "experience_level": exp_level,
            "job_type": j_type,
            "source": f"{self.provider}_official_ats",
            "raw_data": {
                "ats_provider": self.provider,
                "ats_board_key": self.board_key,
                "ats_job_id": self.external_job_id,
                **self.raw_data,
            },
        }


class BaseATSAdapter(ABC):
    """Abstract base class for ATS provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the ATS provider (e.g., 'greenhouse', 'workday')."""
        pass

    @abstractmethod
    async def fetch_board_jobs(self, board_meta: dict[str, Any], client: httpx.AsyncClient) -> list[ATSJob]:
        """
        Fetch all published job listings for a single board.
        
        :param board_meta: Board metadata dictionary containing tokens/urls.
        :param client: Shared httpx.AsyncClient with rate limiting & timeouts.
        :return: List of normalized ATSJob instances.
        """
        pass
