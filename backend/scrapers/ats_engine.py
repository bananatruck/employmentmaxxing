"""
Employmentmaxxing — Async ATS Crawl Engine
Orchestrates high-concurrency, incremental scanning of global Greenhouse & Workday boards,
with rate limiting, backoff jitter, run locks, checkpointing, and safe deactivation.
"""

import asyncio
import random
import time
import traceback
from datetime import datetime
from typing import Any

import httpx
from config import settings
from database import (
    acquire_ats_run_lock,
    get_ats_boards,
    record_ats_checkpoint,
    reconcile_board_deactivations,
    release_ats_run_lock,
    update_ats_board_scan_status,
    upsert_ats_job,
)
from scrapers.adapters import GreenhouseAdapter, WorkdayAdapter
from scrapers.registry import seed_default_registry

USER_AGENT = "Employmentmaxxing/2.1 (contact@employmentmaxxing.internal; +https://github.com/keshjindal/employmentmaxxing)"


class ATSCrawlEngine:
    """Async engine managing multi-provider ATS crawlers with bounded concurrency."""

    def __init__(self):
        self.adapters = {
            "greenhouse": GreenhouseAdapter(),
            "workday": WorkdayAdapter(),
        }
        self.global_limit = getattr(settings, "ats_concurrency_limit", 15)
        self.per_host_limit = getattr(settings, "ats_per_host_concurrency", 3)
        self.max_retries = getattr(settings, "ats_max_retries", 3)

        self.global_semaphore = asyncio.Semaphore(self.global_limit)
        self.host_semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_host_semaphore(self, url: str) -> asyncio.Semaphore:
        try:
            host = httpx.URL(url).host
        except Exception:
            host = "default"
        if host not in self.host_semaphores:
            self.host_semaphores[host] = asyncio.Semaphore(self.per_host_limit)
        return self.host_semaphores[host]

    async def _fetch_with_backoff(self, req_func, url: str, *args, **kwargs) -> httpx.Response:
        """Execute HTTP request with exponential backoff, jitter, and Retry-After support."""
        host_sem = self._get_host_semaphore(url)

        for attempt in range(self.max_retries + 1):
            async with self.global_semaphore:
                async with host_sem:
                    try:
                        resp = await req_func(url, *args, **kwargs)
                        if resp.status_code == 429:
                            retry_after = resp.headers.get("Retry-After")
                            wait_sec = float(retry_after) if retry_after and retry_after.isdigit() else (2.0 ** attempt) + random.uniform(0.1, 0.5)
                            await asyncio.sleep(min(wait_sec, 15.0))
                            continue
                        elif resp.status_code >= 500:
                            wait_sec = (1.5 ** attempt) + random.uniform(0.1, 0.5)
                            await asyncio.sleep(min(wait_sec, 10.0))
                            continue
                        return resp
                    except (httpx.TimeoutException, httpx.NetworkError):
                        if attempt == self.max_retries:
                            raise
                        wait_sec = (1.5 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(min(wait_sec, 10.0))

        raise httpx.RequestError(f"Max retries reached for {url}")

    async def scan_single_board(self, board: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
        """Scan a single ATS board, upsert postings, and reconcile deactivations if 100% successful."""
        provider = board["provider"]
        board_key = board["board_key"]
        adapter = self.adapters.get(provider)

        stats = {
            "provider": provider,
            "board_key": board_key,
            "jobs_found": 0,
            "jobs_new": 0,
            "jobs_updated": 0,
            "jobs_duplicate": 0,
            "jobs_deactivated": 0,
            "filtered_reasons": {},
            "success": False,
            "error": None,
        }

        if not adapter:
            stats["error"] = f"Unsupported provider {provider}"
            return stats

        record_ats_checkpoint(provider, board_key, status="running")

        try:
            raw_jobs = await adapter.fetch_board_jobs(board, client)
            stats["jobs_found"] = len(raw_jobs)

            current_scan_job_ids: list[str] = []

            for job_obj in raw_jobs:
                job_dict = job_obj.to_dict()
                ats_id = job_dict.get("ats_job_id") or job_dict.get("id")
                if ats_id:
                    current_scan_job_ids.append(ats_id)

                res = upsert_ats_job(job_dict)
                if res["inserted"]:
                    if res.get("is_new"):
                        stats["jobs_new"] += 1
                    elif res.get("is_updated"):
                        stats["jobs_updated"] += 1
                else:
                    reason = res.get("reason", "unknown")
                    if reason == "duplicate":
                        stats["jobs_duplicate"] += 1
                    else:
                        stats["filtered_reasons"][reason] = stats["filtered_reasons"].get(reason, 0) + 1

            # Deactivate missing listings ONLY on successful complete scan
            deactivated = reconcile_board_deactivations(provider, board_key, current_scan_job_ids)
            stats["jobs_deactivated"] = deactivated
            stats["success"] = True

            update_ats_board_scan_status(provider, board_key, success=True, job_count=stats["jobs_found"])
            record_ats_checkpoint(provider, board_key, status="completed", jobs_found=stats["jobs_found"])

        except Exception as e:
            err_msg = str(e)
            stats["error"] = err_msg
            update_ats_board_scan_status(provider, board_key, success=False, error=err_msg)
            record_ats_checkpoint(provider, board_key, status="failed", error_message=err_msg)

        return stats


async def run_ats_incremental_scan(providers: list[str] | None = None) -> dict[str, Any]:
    """
    Run incremental ATS scan for target providers.
    Uses DB run lock to prevent concurrent executions.
    """
    if not acquire_ats_run_lock(locked_by="ats_engine"):
        return {
            "status": "already_running",
            "message": "An ATS scan is currently in progress",
            "summary": {},
        }

    try:
        seed_default_registry()
        enabled = providers or getattr(settings, "ats_enabled_providers", ["greenhouse", "workday"])

        all_boards = []
        for p in enabled:
            all_boards.extend(get_ats_boards(provider=p, status=None))

        engine = ATSCrawlEngine()

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=30.0)

        total_stats = {
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "boards_scanned": 0,
            "boards_success": 0,
            "boards_failed": 0,
            "jobs_found": 0,
            "jobs_new": 0,
            "jobs_updated": 0,
            "jobs_duplicate": 0,
            "jobs_deactivated": 0,
            "filtered_reasons": {},
            "errors": [],
        }

        async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
            tasks = [engine.scan_single_board(b, client) for b in all_boards]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception):
                    total_stats["boards_failed"] += 1
                    total_stats["errors"].append(str(res))
                    continue

                total_stats["boards_scanned"] += 1
                if res["success"]:
                    total_stats["boards_success"] += 1
                else:
                    total_stats["boards_failed"] += 1
                    if res.get("error"):
                        total_stats["errors"].append(f"{res['provider']}/{res['board_key']}: {res['error']}")

                total_stats["jobs_found"] += res.get("jobs_found", 0)
                total_stats["jobs_new"] += res.get("jobs_new", 0)
                total_stats["jobs_updated"] += res.get("jobs_updated", 0)
                total_stats["jobs_duplicate"] += res.get("jobs_duplicate", 0)
                total_stats["jobs_deactivated"] += res.get("jobs_deactivated", 0)

                for r, count in res.get("filtered_reasons", {}).items():
                    total_stats["filtered_reasons"][r] = total_stats["filtered_reasons"].get(r, 0) + count

        total_stats["completed_at"] = datetime.now().isoformat()
        return total_stats

    finally:
        release_ats_run_lock()


def run_ats_scan_sync(providers: list[str] | None = None) -> dict[str, Any]:
    """Synchronous entry point for ATS scan execution."""
    return asyncio.run(run_ats_incremental_scan(providers=providers))
