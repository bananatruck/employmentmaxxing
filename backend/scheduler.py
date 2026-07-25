"""
Employmentmaxxing — Background Scheduler
Triggers automatic scrape → deduplicate → analyze → score cycles every N hours.
Integrates JobSpy, Official Company ATS (Greenhouse/Lever APIs), GitHub Community repos, Quantum boards, and HN.
"""

import time
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from scrapers.jobspy_scraper import run_jobspy_scrape
from scrapers.company_ats_scraper import run_company_ats_scrape
from scrapers.github_scraper import run_github_scrape
from scrapers.quantum_scraper import run_quantum_scrape
from scrapers.hn_scraper import run_hn_scrape
from scrapers.deduplicator import deduplicate_jobs
from clean_urls import clean_database_urls
from analysis.jd_parser import run_analysis_pipeline
from analysis.chance_scorer import run_scoring_pipeline


_scheduler = None


def run_full_pipeline():
    """
    Run the entire Employmentmaxxing pipeline:
    1. Scrape official company career portals + job boards + GitHub community
    2. Sanitize and verify all direct apply URLs
    3. Deduplicate listings across sources
    4. Extract structured job description data (Gemini + Regex)
    5. Score jobs against user's profile with 7-factor honest chance scoring
    """
    print(f"\n🚀 [PIPELINE] Starting full pipeline run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    # Step 1: Scrape all sources
    print("Step 1/5: Running scrapers (Company Official ATS, JobSpy, GitHub, Quantum, HN)...")
    ats_stats = run_company_ats_scrape()
    js_stats = run_jobspy_scrape()
    gh_stats = run_github_scrape()
    qj_stats = run_quantum_scrape()
    hn_stats = run_hn_scrape()

    # Step 2: URL Sanitization
    print("\nStep 2/5: Sanitizing and verifying direct apply URLs...")
    clean_database_urls()

    # Step 3: Deduplicate
    print("\nStep 3/5: Deduplicating job listings...")
    dedup_stats = deduplicate_jobs(dry_run=False)

    # Step 4: Analyze
    print("\nStep 4/5: Analyzing new job descriptions...")
    analysis_stats = run_analysis_pipeline(limit=100)

    # Step 5: Score
    print("\nStep 5/5: Scoring jobs against profile...")
    scoring_stats = run_scoring_pipeline(limit=100)

    print(f"✨ [PIPELINE] Complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()

    # Run every N hours (default: 4 hours, configurable in .env)
    _scheduler.add_job(
        run_full_pipeline,
        'interval',
        hours=settings.scrape_interval_hours,
        id='full_pipeline_job',
        replace_existing=True,
    )

    _scheduler.start()
    print(f"⏰ Scheduler started — running pipeline every {settings.scrape_interval_hours} hours")


def stop_scheduler():
    """Stop the scheduler on shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        print("⏰ Scheduler stopped")
