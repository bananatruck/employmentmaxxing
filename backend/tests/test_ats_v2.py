"""
Comprehensive Unit & Integration Test Suite for Employmentmaxxing 2.1 ATS System.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# pyrefly: ignore [missing-import]
import httpx
import database
from config import settings
from scrapers.adapters import GreenhouseAdapter, WorkdayAdapter, ATSJob
from scrapers.adapters.greenhouse import validate_greenhouse_token, is_approved_host as is_gh_approved
from scrapers.adapters.workday import parse_workday_url, parse_workday_relative_date
from scrapers.registry import seed_default_registry, discover_board_from_url, refresh_external_registry
from database import is_ats_run_locked
from scrapers.ats_engine import run_ats_incremental_scan


TEST_DB = str(BASE_DIR / "test_employmentmaxxing.db")
database.DB_PATH = TEST_DB
settings.db_path = TEST_DB


def setup_test_db():
    """Ensure isolated test database schema is initialized and test fixtures cleared before each test run."""
    database.DB_PATH = TEST_DB
    settings.db_path = TEST_DB
    database.init_db()
    database.release_ats_run_lock()
    conn = database.get_connection()
    conn.execute("DELETE FROM jobs WHERE ats_job_id IN ('gh_12345', 'job_1', 'job_2')")
    conn.execute("DELETE FROM ats_boards WHERE board_key IN ('testboard', 'deact_test_board')")
    conn.commit()
    conn.close()





def test_greenhouse_token_and_host_validation():
    assert validate_greenhouse_token("openai") is True
    assert validate_greenhouse_token("scale-ai") is True
    assert validate_greenhouse_token("invalid;drop table") is False
    assert validate_greenhouse_token("token with spaces") is False

    assert is_gh_approved("https://boards-api.greenhouse.io/v1/boards/openai/jobs") is True
    assert is_gh_approved("https://malicious-site.com/v1/boards/openai") is False


def test_workday_url_parsing():
    parsed = parse_workday_url("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
    assert parsed is not None
    assert parsed["tenant"] == "nvidia"
    assert parsed["instance"] == "wd5"
    assert parsed["site"] == "NVIDIAExternalCareerSite"

    parsed_lang = parse_workday_url("https://snowflake.wd1.myworkdayjobs.com/en-US/Snowflake_Careers")
    assert parsed_lang is not None
    assert parsed_lang["tenant"] == "snowflake"
    assert parsed_lang["site"] == "Snowflake_Careers"

    assert parse_workday_url("https://google.com") is None
    assert parse_workday_url("https://invalid_tenant.something.com") is None


def test_workday_relative_date_parsing():
    now_str = datetime.now().strftime("%Y-%m-%d")
    assert parse_workday_relative_date("Posted Today") == now_str
    assert parse_workday_relative_date("Posted 3 Days Ago") != ""
    assert parse_workday_relative_date("Posted 30+ Days Ago") != ""


def test_registry_seeding_and_discovery():
    counts = refresh_external_registry()
    assert counts["total"] > 0
    assert counts["greenhouse"] > 0
    assert counts["workday"] > 0
    assert counts["lever"] > 0
    assert counts["ashby"] > 0
    assert counts["smartrecruiters"] > 0
    assert counts["bamboohr"] > 0

    res_gh = discover_board_from_url("https://boards.greenhouse.io/testboard", company_name="Test Company")
    assert res_gh is not None and res_gh["board_key"] == "testboard"

    res_lever = discover_board_from_url("https://jobs.lever.co/testlever", company_name="Test Lever")
    assert res_lever is not None and res_lever["provider"] == "lever" and res_lever["board_key"] == "testlever"

    res_ashby = discover_board_from_url("https://jobs.ashbyhq.com/testashby", company_name="Test Ashby")
    assert res_ashby is not None and res_ashby["provider"] == "ashby" and res_ashby["board_key"] == "testashby"

    res_smart = discover_board_from_url("https://jobs.smartrecruiters.com/testsmart", company_name="Test Smart")
    assert res_smart is not None and res_smart["provider"] == "smartrecruiters"

    res_bamboo = discover_board_from_url("https://testbamboo.bamboohr.com/careers", company_name="Test Bamboo")
    assert res_bamboo is not None and res_bamboo["provider"] == "bamboohr" and res_bamboo["board_key"] == "testbamboo"


def test_ats_job_upsert_and_content_hash():
    job_data = {
        "ats_provider": "greenhouse",
        "ats_board_key": "test_board",
        "ats_job_id": "gh_12345",
        "title": "Software Engineer Intern 2027",
        "company": "Test AI",
        "location": "San Francisco, CA",
        "description": "Building awesome AI models for students.",
        "apply_url": "https://boards.greenhouse.io/test_board/jobs/gh_12345",
        "date_posted": "2026-07-27",
        "is_remote": True,
    }

    res1 = database.upsert_ats_job(job_data)
    assert res1["inserted"] is True
    assert res1["is_new"] is True

    # Duplicate insertion with unchanged content
    res2 = database.upsert_ats_job(job_data)
    assert res2["inserted"] is False
    assert res2["reason"] == "duplicate"

    # Update with changed description
    job_data_modified = dict(job_data)
    job_data_modified["description"] = "Updated description with PyTorch & CUDA requirements."
    res3 = database.upsert_ats_job(job_data_modified)
    assert res3["inserted"] is True
    assert res3["is_updated"] is True


def test_deactivation_on_success_only():
    provider = "greenhouse"
    board_key = "deact_test_board"

    job1 = {
        "ats_provider": provider,
        "ats_board_key": board_key,
        "ats_job_id": "job_1",
        "title": "AI Research Intern",
        "company": "Deact AI",
        "location": "Remote",
        "description": "Deep learning research.",
        "apply_url": "https://boards.greenhouse.io/deact_test_board/jobs/job_1",
    }
    job2 = {
        "ats_provider": provider,
        "ats_board_key": board_key,
        "ats_job_id": "job_2",
        "title": "SWE Co-op",
        "company": "Deact AI",
        "location": "New York, NY",
        "description": "Backend engineering.",
        "apply_url": "https://boards.greenhouse.io/deact_test_board/jobs/job_2",
    }

    database.upsert_ats_job(job1)
    database.upsert_ats_job(job2)

    # Simulate successful scan where job2 is missing
    deactivated = database.reconcile_board_deactivations(provider, board_key, current_scan_job_ids=["job_1"])
    assert deactivated == 1

    # Verify job2 is now inactive in DB
    conn = database.get_connection()
    row2 = conn.execute("SELECT is_active, closed_at FROM jobs WHERE ats_job_id = 'job_2'").fetchone()
    conn.close()
    assert row2["is_active"] == 0
    assert row2["closed_at"] is not None


def test_run_lock_prevents_overlap():
    assert database.acquire_ats_run_lock("test_runner") is True
    assert database.acquire_ats_run_lock("test_runner_2") is False

    lock_info = database.is_ats_run_locked()
    assert lock_info["is_locked"] == 1
    assert lock_info["locked_by"] == "test_runner"

    database.release_ats_run_lock()
    assert database.is_ats_run_locked()["is_locked"] == 0


if __name__ == "__main__":
    setup_test_db()
    test_greenhouse_token_and_host_validation()
    print("✅ Greenhouse token & host validation test passed")
    test_workday_url_parsing()
    print("✅ Workday URL parsing test passed")
    test_workday_relative_date_parsing()
    print("✅ Workday relative date parsing test passed")
    test_registry_seeding_and_discovery()
    print("✅ Registry seeding & discovery test passed")
    test_ats_job_upsert_and_content_hash()
    print("✅ ATS job upsert & content hash test passed")
    test_deactivation_on_success_only()
    print("✅ Deactivation on success test passed")
    test_run_lock_prevents_overlap()
    print("✅ Run lock prevention test passed")
    print("\n🎉 ALL ATS 2.1 UNIT & INTEGRATION TESTS PASSED SUCCESSFULLY!")
