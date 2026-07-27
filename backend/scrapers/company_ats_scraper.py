"""
Employmentmaxxing — Direct Company ATS Scraper
Directly queries official career APIs of top tech companies and AI startups.
Excludes Palantir and Defense contractors.
"""

import time
import requests
import traceback
from datetime import datetime

from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end
from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote
from clean_html import strip_html, is_senior_role
from utils.exclusion_filter import is_job_eligible


# Top Tech Companies & AI Startups on Greenhouse
GREENHOUSE_COMPANIES = [
    "scaleai", "figma", "vercel", "retool", "modal", "perplexity", "togetherai",
    "pinecone", "weaviate", "replit", "huggingface", "cohere", "harvey", "midjourney",
    "cognition", "elevenlabs", "anysphere", "langchain", "groq", "baseten", "octoai",
    "stripe", "airbnb", "doordash", "coinbase", "instacart", "cloudflare", "roblox",
    "pinterest", "discord", "duolingo", "plaid", "brex", "ramp", "notion", "datadog",
    "splunk", "elastic", "mongodb", "hashicorp", "gitlab", "confluent", "twilio",
    "asana", "zapier", "toast", "robinhood", "box", "samsara", "rubrik", "databricks",
    "snowflake", "chime", "gusto", "flexport", "opensea", "dbtlabs",
    "temporal", "astronomer", "launchdarkly", "postman", "sentry", "supabase",
    "neon", "planetscale", "upstash", "flyio", "render", "clerk", "resend",
    "mistral", "writer", "unstructured", "chroma", "qdrant", "deepgram", "assemblyai",
    "synthesia", "fireworksai", "linear", "raycast", "ngrok", "tailscale", "railway"
]

# Top Tech Companies & AI Startups on Lever (Palantir removed)
LEVER_COMPANIES = [
    "anthropic", "openai", "netflix", "spotify", "datadog", "brex",
    "ramp", "cursor", "scale", "scaleai", "midjourney", "together", "cohere",
    "huggingface", "mistral", "anyscale", "cerebras", "deepmind", "nomic",
    "langchain", "vllm", "perplexity", "stability", "runway", "adept", "inflection",
    "lumaai", "pika", "sora", "characterai", "relationalai"
]

TARGET_KEYWORDS = [
    "intern", "internship", "co-op", "coop", "student", "university",
    "new grad", "entry", "junior", "early career",
    "machine learning", "ai ", "software", "deep learning", "nlp",
    "computer vision", "quantum", "data science", "mlops", "backend", "frontend",
    "full stack", "infrastructure", "systems", "platform", "cloud",
]


def _scrape_greenhouse_company(company_slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    jobs = []

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jobs

        data = resp.json()
        raw_jobs = data.get("jobs", [])
        company_name = company_slug.replace("-", " ").title()

        for j in raw_jobs:
            title = strip_html(j.get("title", ""))
            if is_senior_role(title) or not any(kw in title.lower() for kw in TARGET_KEYWORDS):
                continue

            location_obj = j.get("location", {})
            location_name = strip_html(location_obj.get("name", "US / Remote") if isinstance(location_obj, dict) else str(location_obj))

            content = strip_html(j.get("content", ""))
            apply_url = j.get("absolute_url", f"https://boards.greenhouse.io/{company_slug}/jobs/{j.get('id')}")

            job_type = classify_job_type(title, content)
            exp_level = detect_experience_level(title, content)

            job = {
                "id": generate_job_id(company_name, title, location_name),
                "title": title,
                "company": company_name,
                "location": location_name,
                "is_remote": is_remote(title, location_name, content),
                "description": content[:5000] if content else f"Official position at {company_name}: {title}.",
                "apply_url": apply_url,
                "salary_min": None,
                "salary_max": None,
                "date_posted": j.get("updated_at", "")[:10],
                "source": "company_official_ats",
                "experience_level": exp_level,
                "job_type": job_type,
                "raw_data": {"company_slug": company_slug, "ats": "greenhouse", "job_id": j.get("id")},
            }

            eligible, _ = is_job_eligible(job)
            if eligible:
                jobs.append(job)

    except Exception:
        pass

    return jobs


def _scrape_lever_company(company_slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    jobs = []

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jobs

        raw_jobs = resp.json()
        if not isinstance(raw_jobs, list):
            return jobs

        company_name = company_slug.replace("-", " ").title()

        for j in raw_jobs:
            title = strip_html(j.get("text", ""))
            if is_senior_role(title) or not any(kw in title.lower() for kw in TARGET_KEYWORDS):
                continue

            categories = j.get("categories", {})
            location_name = strip_html(categories.get("location", "US / Remote") if isinstance(categories, dict) else "US / Remote")

            desc_plain = strip_html(j.get("descriptionPlain", ""))
            apply_url = j.get("applyUrl", j.get("hostedUrl", ""))

            job_type = classify_job_type(title, desc_plain)
            exp_level = detect_experience_level(title, desc_plain)

            job = {
                "id": generate_job_id(company_name, title, location_name),
                "title": title,
                "company": company_name,
                "location": location_name,
                "is_remote": is_remote(title, location_name, desc_plain),
                "description": desc_plain[:5000] if desc_plain else f"Official position at {company_name}: {title}.",
                "apply_url": apply_url,
                "salary_min": None,
                "salary_max": None,
                "date_posted": datetime.now().strftime("%Y-%m-%d"),
                "source": "company_official_ats",
                "experience_level": exp_level,
                "job_type": job_type,
                "raw_data": {"company_slug": company_slug, "ats": "lever", "job_id": j.get("id")},
            }

            eligible, _ = is_job_eligible(job)
            if eligible:
                jobs.append(job)

    except Exception:
        pass

    return jobs


def run_company_ats_scrape() -> dict:
    log_id = log_scrape_start("company_official_ats")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    print("🏢 Scraping official company career portals (Greenhouse & Lever APIs)...")

    for company in GREENHOUSE_COMPANIES:
        try:
            jobs = _scrape_greenhouse_company(company)
            if jobs:
                for job in jobs:
                    is_new = insert_job(job)
                    stats["jobs_found"] += 1
                    if is_new:
                        stats["jobs_new"] += 1
                    else:
                        stats["jobs_duplicate"] += 1
        except Exception as e:
            stats["errors"].append(f"Greenhouse {company}: {e}")
        time.sleep(0.05)

    for company in LEVER_COMPANIES:
        try:
            jobs = _scrape_lever_company(company)
            if jobs:
                for job in jobs:
                    is_new = insert_job(job)
                    stats["jobs_found"] += 1
                    if is_new:
                        stats["jobs_new"] += 1
                    else:
                        stats["jobs_duplicate"] += 1
        except Exception as e:
            stats["errors"].append(f"Lever {company}: {e}")
        time.sleep(0.05)

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ Official Company ATS scrape complete: {stats['jobs_found']} found, {stats['jobs_new']} new, {stats['jobs_duplicate']} dupes")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_company_ats_scrape()
    print(stats)
