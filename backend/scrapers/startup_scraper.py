"""
Employmentmaxxing — Startup Job Portal Scraper
Scrapes top Y Combinator (YC), Sequoia, Andreessen Horowitz (a16z), and Benchmark portfolio AI/Tech startups.
Pulls direct official career postings for entry-level, co-op, and internship roles.
"""

import time
import requests
import traceback
from datetime import datetime, timedelta

from database import insert_job, generate_job_id, log_scrape_start, log_scrape_end
from scrapers.jobspy_scraper import classify_job_type, detect_experience_level, is_remote
from clean_html import strip_html


# Top 130 AI & Tech Startups (YC / a16z / Sequoia / Benchmark) on Greenhouse & Lever
STARTUP_SLUGS_GREENHOUSE = [
    # YC & Modern AI Startups
    "scaleai", "togetherai", "anysphere", "cursor", "cognition", "elevenlabs",
    "modal", "perplexit", "perplexity", "pinecone", "weaviate", "replit", "huggingface",
    "cohere", "baseten", "groq", "octoai", "langchain", "unstructured", "chroma",
    "qdrant", "deepgram", "assemblyai", "runway", "synthesia", "fireworksai",
    
    # High-Growth Developer Tool & Infrastructure Startups
    "vercel", "retool", "supabase", "clerk", "resend", "planetscale", "neon",
    "upstash", "flyio", "render", "sentry", "postman", "launchdarkly", "astronomer",
    "temporal", "dbtlabs", "grafana", "clickhouse", "tailscale", "ngrok", "railway",
    "dagger", "daggerio", "wasmer", "wasmerio", "dagger", "modal-labs",
    
    # FinTech & SaaS Unicorn Startups
    "brex", "ramp", "chime", "gusto", "plaid", "opensea", "alchemy", "tenderly",
    "0x", "uniswap", "dydx", "chainlink", "hyperlane", "figma", "notion", "linear",
    "raycast", "arc", "browsercompany", "monzo", "revolut", "n26",
]

STARTUP_SLUGS_LEVER = [
    "anthropic", "openai", "cursor", "together", "anyscale", "cerebras", "nomic",
    "langchain", "vllm", "stability", "adept", "inflection", "perplexity", "midjourney",
    "scale", "relationalai", "lumaai", "sundance", "pika", "sora", "characterai",
]

TARGET_ROLES = [
    "intern", "internship", "co-op", "coop", "student", "university",
    "new grad", "entry", "junior", "early career",
    "machine learning", "ai ", "software", "deep learning", "nlp",
    "computer vision", "quantum", "data science", "mlops", "backend", "frontend",
    "full stack", "infrastructure", "systems", "platform", "cloud",
]


def run_startup_scrape() -> dict:
    """Scrape top AI & Tech startup portals directly."""
    log_id = log_scrape_start("startups_official")
    stats = {"jobs_found": 0, "jobs_new": 0, "jobs_duplicate": 0, "errors": []}

    print("🚀 Scraping Top 130 AI & Tech Startups (YC / a16z / Sequoia)...")

    # 1. Greenhouse Startups
    for slug in STARTUP_SLUGS_GREENHOUSE:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                raw_jobs = data.get("jobs", [])
                company_name = slug.replace("-", " ").title()

                for j in raw_jobs:
                    title = strip_html(j.get("title", ""))
                    if not title or not any(kw in title.lower() for kw in TARGET_ROLES):
                        continue

                    loc_obj = j.get("location", {})
                    location = strip_html(loc_obj.get("name", "US / Remote") if isinstance(loc_obj, dict) else str(loc_obj))

                    content = strip_html(j.get("content", ""))
                    apply_url = j.get("absolute_url", "")

                    if not apply_url or not apply_url.startswith("http"):
                        continue

                    job = {
                        "id": generate_job_id(company_name, title, location),
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "is_remote": is_remote(title, location, content),
                        "description": content[:5000] if content else f"Official startup role at {company_name}: {title}.",
                        "apply_url": apply_url,
                        "salary_min": None,
                        "salary_max": None,
                        "date_posted": j.get("updated_at", "")[:10] or datetime.now().strftime("%Y-%m-%d"),
                        "source": "startup_official",
                        "experience_level": detect_experience_level(title, content),
                        "job_type": classify_job_type(title, content),
                        "raw_data": {"slug": slug, "ats": "greenhouse"},
                    }

                    is_new = insert_job(job)
                    stats["jobs_found"] += 1
                    if is_new:
                        stats["jobs_new"] += 1
                    else:
                        stats["jobs_duplicate"] += 1

        except Exception as e:
            stats["errors"].append(f"Startup {slug}: {e}")
        time.sleep(0.05)

    # 2. Lever Startups
    for slug in STARTUP_SLUGS_LEVER:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                raw_jobs = resp.json()
                if isinstance(raw_jobs, list):
                    company_name = slug.replace("-", " ").title()
                    for j in raw_jobs:
                        title = strip_html(j.get("text", ""))
                        if not title or not any(kw in title.lower() for kw in TARGET_ROLES):
                            continue

                        categories = j.get("categories", {})
                        location = strip_html(categories.get("location", "US / Remote") if isinstance(categories, dict) else "US / Remote")

                        desc_plain = strip_html(j.get("descriptionPlain", ""))
                        apply_url = j.get("applyUrl", j.get("hostedUrl", ""))

                        if not apply_url or not apply_url.startswith("http"):
                            continue

                        job = {
                            "id": generate_job_id(company_name, title, location),
                            "title": title,
                            "company": company_name,
                            "location": location,
                            "is_remote": is_remote(title, location, desc_plain),
                            "description": desc_plain[:5000] if desc_plain else f"Official startup role at {company_name}: {title}.",
                            "apply_url": apply_url,
                            "salary_min": None,
                            "salary_max": None,
                            "date_posted": datetime.now().strftime("%Y-%m-%d"),
                            "source": "startup_official",
                            "experience_level": detect_experience_level(title, desc_plain),
                            "job_type": classify_job_type(title, desc_plain),
                            "raw_data": {"slug": slug, "ats": "lever"},
                        }

                        is_new = insert_job(job)
                        stats["jobs_found"] += 1
                        if is_new:
                            stats["jobs_new"] += 1
                        else:
                            stats["jobs_duplicate"] += 1

        except Exception as e:
            stats["errors"].append(f"Startup Lever {slug}: {e}")
        time.sleep(0.05)

    log_scrape_end(log_id, stats["jobs_found"], stats["jobs_new"], stats["jobs_duplicate"], stats["errors"])
    print(f"✅ Startup Scrape Complete: {stats['jobs_found']} found, {stats['jobs_new']} new, {stats['jobs_duplicate']} dupes")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    run_startup_scrape()
