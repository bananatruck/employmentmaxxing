# Employmentmaxxing 2.1 — Global ATS Discovery & Incremental Crawler Plan

Employmentmaxxing will discover boards globally, scan them incrementally, normalize matching postings into SQLite, deactivate removed listings, and expose coverage through the existing API.

---

## 1. ATS Board Registry and Discovery

- **Database Table (`ats_boards`)**:
  - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
  - `provider`: TEXT NOT NULL ('greenhouse', 'workday', etc.)
  - `board_key`: TEXT NOT NULL (unique per provider)
  - `company_name`: TEXT NOT NULL
  - `board_token`: TEXT (for Greenhouse)
  - `tenant`: TEXT (for Workday)
  - `instance`: TEXT (for Workday)
  - `site`: TEXT (for Workday)
  - `canonical_url`: TEXT NOT NULL
  - `discovery_source`: TEXT NOT NULL
  - `discovered_at`: TEXT NOT NULL
  - `last_successful_scan`: TEXT
  - `next_scan`: TEXT
  - `failure_count`: INTEGER DEFAULT 0
  - `status`: TEXT DEFAULT 'active' ('active', 'failing', 'disabled')
  - `last_job_count`: INTEGER DEFAULT 0
  - `http_cache_meta`: TEXT DEFAULT '{}'
  - UNIQUE(`provider`, `board_key`)

- **Seeding Sources**:
  1. Existing `GREENHOUSE_COMPANIES` & `LEVER_COMPANIES` in `company_ats_scraper.py`.
  2. Downloaded and locally cached versioned Greenhouse/Workday dataset (`backend/data/external_boards_cache.json`).
  3. ATS URLs extracted dynamically from startup, GitHub, and JobSpy scrapers.
  4. User-maintained override file (`backend/data/ats_overrides.json` or `.yaml`).

- **Validation & Security**:
  - Enforce strict regex validation on board tokens/tenants (`^[a-zA-Z0-9_\-]+$`).
  - Only construct request URLs targeting approved ATS domains (`boards-api.greenhouse.io`, `*.myworkdayjobs.com`).

- **Lifecycle & Telemetry**:
  - Refresh external registry daily while retaining existing discovered boards even if omitted from fresh sources.
  - Track registry size, scan success rate, and last successful run time as coverage metrics.

---

## 2. Provider Adapters

Refactor `company_ats_scraper.py` into shared provider modules (`backend/scrapers/adapters/`) returning normalized `ATSJob` objects.

- **Normalized Contract (`ATSJob`)**:
  - `provider`: str
  - `board_key`: str
  - `external_job_id`: str
  - `title`: str
  - `company`: str
  - `location`: str
  - `description`: str
  - `apply_url`: str
  - `posted_at`: str | None
  - `updated_at`: str | None
  - `is_remote`: bool
  - `raw_data`: dict

- **Greenhouse Adapter (`backend/scrapers/adapters/greenhouse.py`)**:
  - Query: `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
  - Extract fields: job ID, title, company (using board org name), location, content/description, departments, offices, language, `absolute_url`, `updated_at`.
  - Reject redirects to external domains or malformed responses.
  - Single unpaginated fetch per board.

- **Workday Adapter (`backend/scrapers/adapters/workday.py`)**:
  - Parse canonical Workday URLs: `https://{tenant}.{instance}.myworkdayjobs.com/{site}`.
  - Query public CXS jobs endpoint: `POST https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`.
  - Paginate with `limit`, `offset`, and reported `total`.
  - Configurable safety ceilings (`max_pages`, `max_jobs`).
  - Termination rules: short page, reported total reached, or repeating page job ID detection.
  - Conservative relative date parsing ("Posted 3 Days Ago" -> calculated date ISO, keeping original raw label).
  - Apply title/location pre-filters on listing results before fetching detail endpoints (`POST /wday/cxs/{tenant}/{site}/job/{job_path}`).

---

## 3. Crawl Engine and Reliability (`backend/scrapers/ats_engine.py`)

- **HTTP Client**:
  - `httpx.AsyncClient` with global (e.g., max 20) and host-level semaphores.
  - Explicit timeouts (connect: 5s, read: 15s).
  - Browser-identifying user-agent & contact headers (`Employmentmaxxing/2.1 (contact@employmentmaxxing.internal)`).
  - Exponential backoff with jitter for 429 / 5xx / timeouts; parse and respect `Retry-After`.

- **Queue & Scheduling**:
  - Bounded asyncio worker queues.
  - Dynamic board frequency: Frequently scan active/high-yield boards; back off failing boards up to 24-48 hours.
  - DB-backed run lock (`ats_run_lock`) preventing concurrent scheduled or manual runs.
  - Board-level checkpointing (`ats_scan_checkpoints` table) allowing crash recovery without re-running entire scans.
  - Local caching of downloaded discovery datasets.

---

## 4. Database Ingestion & Job Lifecycle

- **Database Schema Extensions (`jobs` table)**:
  - `ats_provider`: TEXT
  - `ats_board_key`: TEXT
  - `ats_job_id`: TEXT
  - `first_seen_at`: TEXT
  - `last_seen_at`: TEXT
  - `source_updated_at`: TEXT
  - `content_hash`: TEXT
  - `closed_at`: TEXT
  - UNIQUE INDEX `idx_jobs_ats_unique ON jobs(ats_provider, ats_board_key, ats_job_id)`

- **Ingestion & Deactivation Rules**:
  - Exact ATS identity upserts based on `(ats_provider, ats_board_key, ats_job_id)`.
  - Update `content_hash` (MD5/SHA256 of title + location + description). Re-run parsing/scoring if hash changes.
  - Preserve `first_seen_at`, application history, and scores.
  - Apply eligibility filters (`is_us_location`, `is_job_eligible`) before insertion; record filtered counts by reason.
  - **Deactivation**: After a *complete successful board scan*, mark any active job for that board missing from the scan as `is_active = FALSE` and `closed_at = now_iso`.
  - NEVER deactivate jobs if a board scan failed or was partial/interrupted.
  - Closed jobs linked to applications are retained (marked inactive, not deleted).

---

## 5. Scheduling and API Integration

- **Scheduler Jobs (`backend/scheduler.py`)**:
  - Daily: External ATS registry refresh.
  - Every 3 Hours: Greenhouse incremental scan.
  - Continuous/Batched: Workday incremental scan.
  - Post-Scan: Expiration reconciliation per board.
  - Weekly: Full coverage audit & cleanup.

- **API Endpoints (`backend/routes/scrape.py`)**:
  - `POST /api/scrape/trigger?providers=greenhouse,workday` (Returns 409 if run lock is held).
  - `GET /api/scrape/status` (Provides running state, queue depth, boards count, jobs summary, filter reasons breakdown, last coverage timestamp).
  - `GET /api/jobs` (Optional `ats_provider` and `ats_board_key` query filters).

---

## Delivery Phases

1. Schema migrations, `ATSJob` interface, exact ATS identity upsert, database helpers.
2. Refactored Greenhouse adapter & async engine.
3. Workday CXS adapter with pagination, detail hydration, safety caps.
4. Registry discovery, URL parsing, local dataset caching, checkpointing, backoff.
5. Lifecycle deactivation, scheduler updates, API endpoints, status telemetry.
6. Fixture testing, validation, and staged rollout.
