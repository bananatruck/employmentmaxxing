"""
Employmentmaxxing — Database Layer
SQLite database setup, schema, and helper functions.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from config import settings


DB_PATH = settings.db_path


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- Core job listing
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            is_remote BOOLEAN DEFAULT FALSE,
            description TEXT,
            apply_url TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            date_posted TEXT,
            date_scraped TEXT,
            source TEXT,
            all_sources TEXT DEFAULT '[]',
            experience_level TEXT,
            job_type TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            raw_data TEXT
        );

        -- Structured analysis from Gemini
        CREATE TABLE IF NOT EXISTS job_analysis (
            job_id TEXT PRIMARY KEY REFERENCES jobs(id),
            required_skills TEXT DEFAULT '[]',
            preferred_skills TEXT DEFAULT '[]',
            education_required TEXT,
            years_experience INTEGER DEFAULT 0,
            tech_stack TEXT DEFAULT '[]',
            visa_sponsorship TEXT DEFAULT 'unknown',
            red_flags TEXT DEFAULT '[]',
            green_flags TEXT DEFAULT '[]',
            team_focus TEXT,
            analyzed_at TEXT
        );

        -- User profile (single row)
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT DEFAULT '',
            university TEXT DEFAULT '',
            graduation_year INTEGER DEFAULT 2027,
            degree TEXT DEFAULT 'BS Computer Science',
            gpa_range TEXT DEFAULT '',
            skills TEXT DEFAULT '[]',
            projects TEXT DEFAULT '[]',
            preferred_locations TEXT DEFAULT '[]',
            open_to_remote BOOLEAN DEFAULT TRUE,
            target_roles TEXT DEFAULT '["AI/ML", "SWE", "Quantum"]',
            additional_context TEXT DEFAULT ''
        );

        -- Chance scores
        CREATE TABLE IF NOT EXISTS chance_scores (
            job_id TEXT PRIMARY KEY REFERENCES jobs(id),
            overall_score INTEGER DEFAULT 0,
            verdict TEXT DEFAULT '',
            skill_match_pct REAL DEFAULT 0.0,
            education_fit REAL DEFAULT 0.0,
            experience_fit REAL DEFAULT 0.0,
            preferred_skill_pct REAL DEFAULT 0.0,
            competition_estimate REAL DEFAULT 0.0,
            location_fit REAL DEFAULT 0.0,
            ai_assessment REAL DEFAULT 0.0,
            honest_take TEXT DEFAULT '',
            improvement_tips TEXT DEFAULT '[]',
            apply_priority TEXT DEFAULT 'MEDIUM',
            scored_at TEXT
        );

        -- Application tracking
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT REFERENCES jobs(id),
            status TEXT DEFAULT 'interested',
            applied_date TEXT,
            notes TEXT DEFAULT '',
            follow_up_date TEXT,
            response_received BOOLEAN DEFAULT FALSE,
            updated_at TEXT
        );

        -- Scrape log
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            completed_at TEXT,
            source TEXT,
            jobs_found INTEGER DEFAULT 0,
            jobs_new INTEGER DEFAULT 0,
            jobs_duplicate INTEGER DEFAULT 0,
            errors TEXT DEFAULT '[]',
            status TEXT DEFAULT 'running'
        );

        -- Create indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_jobs_date_posted ON jobs(date_posted);
        CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
        CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type);
        CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active);
        CREATE INDEX IF NOT EXISTS idx_chance_scores_overall ON chance_scores(overall_score);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
    """)

    # Ensure default profile row exists
    cursor.execute("SELECT COUNT(*) FROM user_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO user_profile (id, name, graduation_year, degree, target_roles, open_to_remote)
            VALUES (1, '', 2027, 'BS Computer Science', '["AI/ML", "SWE", "Quantum"]', TRUE)
        """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


def generate_job_id(company: str, title: str, location: str = "") -> str:
    """Generate a deterministic job ID from company + title + location."""
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{location.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Job CRUD ────────────────────────────────────────────────────────────

def insert_job(job_data: dict) -> bool:
    """Insert a job into the database. Returns True if new, False if duplicate."""
    conn = get_connection()
    cursor = conn.cursor()

    job_id = job_data.get("id") or generate_job_id(
        job_data.get("company", ""),
        job_data.get("title", ""),
        job_data.get("location", ""),
    )

    # Check if job already exists
    existing = cursor.execute("SELECT id, all_sources FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if existing:
        # Merge sources
        current_sources = json.loads(existing["all_sources"] or "[]")
        new_source = job_data.get("source", "unknown")
        if new_source not in current_sources:
            current_sources.append(new_source)
            cursor.execute(
                "UPDATE jobs SET all_sources = ? WHERE id = ?",
                (json.dumps(current_sources), job_id),
            )
            conn.commit()
        conn.close()
        return False  # Duplicate

    now = datetime.now().isoformat()
    cursor.execute(
        """INSERT INTO jobs (id, title, company, location, is_remote, description,
           apply_url, salary_min, salary_max, date_posted, date_scraped, source,
           all_sources, experience_level, job_type, is_active, raw_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            job_data.get("title", ""),
            job_data.get("company", ""),
            job_data.get("location", ""),
            job_data.get("is_remote", False),
            job_data.get("description", ""),
            job_data.get("apply_url", ""),
            job_data.get("salary_min"),
            job_data.get("salary_max"),
            job_data.get("date_posted", ""),
            now,
            job_data.get("source", "unknown"),
            json.dumps([job_data.get("source", "unknown")]),
            job_data.get("experience_level", "intern"),
            job_data.get("job_type", ""),
            True,
            json.dumps(job_data.get("raw_data", {})),
        ),
    )
    conn.commit()
    conn.close()
    return True  # New job


def get_jobs(
    limit: int = 50,
    offset: int = 0,
    job_type: str | None = None,
    min_score: int | None = None,
    source: str | None = None,
    search: str | None = None,
    sort_by: str = "date_scraped",
    sort_order: str = "desc",
) -> list[dict]:
    """Fetch jobs with optional filters."""
    conn = get_connection()
    query = """
        SELECT j.*, cs.overall_score, cs.verdict, cs.apply_priority
        FROM jobs j
        LEFT JOIN chance_scores cs ON j.id = cs.job_id
        WHERE j.is_active = TRUE
    """
    params: list = []

    if job_type:
        query += " AND j.job_type = ?"
        params.append(job_type)
    if min_score is not None:
        query += " AND cs.overall_score >= ?"
        params.append(min_score)
    if source:
        query += " AND j.source = ?"
        params.append(source)
    if search:
        query += " AND (j.title LIKE ? OR j.company LIKE ? OR j.description LIKE ?)"
        params.extend([f"%{search}%"] * 3)

    # Validate sort column
    allowed_sorts = {"date_scraped", "date_posted", "company", "title", "overall_score"}
    if sort_by not in allowed_sorts:
        sort_by = "date_scraped"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    if sort_by == "overall_score":
        query += f" ORDER BY cs.overall_score {order} NULLS LAST"
    else:
        query += f" ORDER BY j.{sort_by} {order}"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_by_id(job_id: str) -> dict | None:
    """Get full job detail including analysis and score."""
    conn = get_connection()
    row = conn.execute(
        """SELECT j.*, ja.required_skills, ja.preferred_skills, ja.education_required,
           ja.years_experience, ja.tech_stack, ja.visa_sponsorship, ja.red_flags,
           ja.green_flags, ja.team_focus,
           cs.overall_score, cs.verdict, cs.skill_match_pct, cs.education_fit,
           cs.experience_fit, cs.preferred_skill_pct, cs.competition_estimate,
           cs.location_fit, cs.ai_assessment, cs.honest_take, cs.improvement_tips,
           cs.apply_priority
        FROM jobs j
        LEFT JOIN job_analysis ja ON j.id = ja.job_id
        LEFT JOIN chance_scores cs ON j.id = cs.job_id
        WHERE j.id = ?""",
        (job_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_job_count(job_type: str | None = None) -> int:
    """Get total number of active jobs."""
    conn = get_connection()
    if job_type:
        count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE is_active = TRUE AND job_type = ?",
            (job_type,),
        ).fetchone()[0]
    else:
        count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE is_active = TRUE"
        ).fetchone()[0]
    conn.close()
    return count


def get_unanalyzed_jobs(limit: int = 50) -> list[dict]:
    """Get jobs that haven't been analyzed by the AI yet."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT j.* FROM jobs j
           LEFT JOIN job_analysis ja ON j.id = ja.job_id
           WHERE ja.job_id IS NULL AND j.description IS NOT NULL AND j.description != ''
           ORDER BY j.date_scraped DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unscored_jobs(limit: int = 50) -> list[dict]:
    """Get jobs that have analysis but no chance score yet."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT j.*, ja.required_skills, ja.preferred_skills, ja.education_required,
           ja.years_experience, ja.tech_stack, ja.team_focus
           FROM jobs j
           INNER JOIN job_analysis ja ON j.id = ja.job_id
           LEFT JOIN chance_scores cs ON j.id = cs.job_id
           WHERE cs.job_id IS NULL
           ORDER BY j.date_scraped DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_analysis(job_id: str, analysis: dict):
    """Save AI analysis results for a job."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO job_analysis
           (job_id, required_skills, preferred_skills, education_required,
            years_experience, tech_stack, visa_sponsorship, red_flags,
            green_flags, team_focus, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            json.dumps(analysis.get("required_skills", [])),
            json.dumps(analysis.get("preferred_skills", [])),
            analysis.get("education_required", ""),
            analysis.get("years_experience", 0),
            json.dumps(analysis.get("tech_stack", [])),
            analysis.get("visa_sponsorship", "unknown"),
            json.dumps(analysis.get("red_flags", [])),
            json.dumps(analysis.get("green_flags", [])),
            analysis.get("team_focus", ""),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def save_chance_score(job_id: str, score: dict):
    """Save chance score results for a job."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO chance_scores
           (job_id, overall_score, verdict, skill_match_pct, education_fit,
            experience_fit, preferred_skill_pct, competition_estimate,
            location_fit, ai_assessment, honest_take, improvement_tips,
            apply_priority, scored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            score.get("overall_score", 0),
            score.get("verdict", ""),
            score.get("skill_match_pct", 0.0),
            score.get("education_fit", 0.0),
            score.get("experience_fit", 0.0),
            score.get("preferred_skill_pct", 0.0),
            score.get("competition_estimate", 0.0),
            score.get("location_fit", 0.0),
            score.get("ai_assessment", 0.0),
            score.get("honest_take", ""),
            json.dumps(score.get("improvement_tips", [])),
            score.get("apply_priority", "MEDIUM"),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ── Profile CRUD ────────────────────────────────────────────────────────

def get_profile() -> dict:
    """Get the user profile."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    if row:
        profile = dict(row)
        # Parse JSON fields
        for field in ["skills", "projects", "preferred_locations", "target_roles"]:
            if profile.get(field):
                try:
                    profile[field] = json.loads(profile[field])
                except (json.JSONDecodeError, TypeError):
                    profile[field] = []
        return profile
    return {}


def save_profile(profile_data: dict):
    """Update the user profile."""
    conn = get_connection()
    # Serialize JSON fields
    for field in ["skills", "projects", "preferred_locations", "target_roles"]:
        if field in profile_data and isinstance(profile_data[field], (list, dict)):
            profile_data[field] = json.dumps(profile_data[field])

    conn.execute(
        """UPDATE user_profile SET
           name = ?, university = ?, graduation_year = ?, degree = ?,
           gpa_range = ?, skills = ?, projects = ?, preferred_locations = ?,
           open_to_remote = ?, target_roles = ?, additional_context = ?
           WHERE id = 1""",
        (
            profile_data.get("name", ""),
            profile_data.get("university", ""),
            profile_data.get("graduation_year", 2027),
            profile_data.get("degree", "BS Computer Science"),
            profile_data.get("gpa_range", ""),
            profile_data.get("skills", "[]"),
            profile_data.get("projects", "[]"),
            profile_data.get("preferred_locations", "[]"),
            profile_data.get("open_to_remote", True),
            profile_data.get("target_roles", '["AI/ML", "SWE", "Quantum"]'),
            profile_data.get("additional_context", ""),
        ),
    )
    conn.commit()
    conn.close()


# ── Application Tracking ────────────────────────────────────────────────

def get_applications(status: str | None = None) -> list[dict]:
    """Get tracked applications."""
    conn = get_connection()
    if status:
        rows = conn.execute(
            """SELECT a.*, j.title, j.company, j.location, j.apply_url,
               cs.overall_score, cs.verdict
               FROM applications a
               JOIN jobs j ON a.job_id = j.id
               LEFT JOIN chance_scores cs ON a.job_id = cs.job_id
               WHERE a.status = ?
               ORDER BY a.updated_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT a.*, j.title, j.company, j.location, j.apply_url,
               cs.overall_score, cs.verdict
               FROM applications a
               JOIN jobs j ON a.job_id = j.id
               LEFT JOIN chance_scores cs ON a.job_id = cs.job_id
               ORDER BY a.updated_at DESC"""
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_application(job_id: str, status: str = "interested") -> int:
    """Add a job to the application tracker."""
    conn = get_connection()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO applications (job_id, status, updated_at)
           VALUES (?, ?, ?)""",
        (job_id, status, now),
    )
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id


def update_application(app_id: int, updates: dict):
    """Update an application's status and/or notes."""
    conn = get_connection()
    now = datetime.now().isoformat()
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [app_id]
    conn.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_application(app_id: int):
    """Remove an application from the tracker."""
    conn = get_connection()
    conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


# ── Scrape Log ──────────────────────────────────────────────────────────

def log_scrape_start(source: str) -> int:
    """Log the start of a scrape operation."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO scrape_log (started_at, source, status) VALUES (?, ?, 'running')",
        (datetime.now().isoformat(), source),
    )
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def log_scrape_end(log_id: int, jobs_found: int, jobs_new: int, jobs_duplicate: int, errors: list = None):
    """Log the completion of a scrape operation."""
    conn = get_connection()
    conn.execute(
        """UPDATE scrape_log SET completed_at = ?, jobs_found = ?, jobs_new = ?,
           jobs_duplicate = ?, errors = ?, status = 'completed'
           WHERE id = ?""",
        (
            datetime.now().isoformat(),
            jobs_found,
            jobs_new,
            jobs_duplicate,
            json.dumps(errors or []),
            log_id,
        ),
    )
    conn.commit()
    conn.close()


def get_last_scrape() -> dict | None:
    """Get the most recent completed scrape log."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM scrape_log WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Analytics Queries ───────────────────────────────────────────────────

def get_analytics_stats() -> dict:
    """Get aggregated analytics data."""
    conn = get_connection()

    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = TRUE").fetchone()[0]
    total_scored = conn.execute("SELECT COUNT(*) FROM chance_scores").fetchone()[0]
    total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    # Average score
    avg_score_row = conn.execute("SELECT AVG(overall_score) FROM chance_scores").fetchone()
    avg_score = round(avg_score_row[0] or 0, 1)

    # Score distribution
    score_dist = conn.execute("""
        SELECT
            CASE
                WHEN overall_score >= 81 THEN 'excellent'
                WHEN overall_score >= 61 THEN 'strong'
                WHEN overall_score >= 31 THEN 'moderate'
                ELSE 'reach'
            END as tier,
            COUNT(*) as count
        FROM chance_scores
        GROUP BY tier
    """).fetchall()

    # Jobs by type
    jobs_by_type = conn.execute("""
        SELECT job_type, COUNT(*) as count
        FROM jobs WHERE is_active = TRUE AND job_type != ''
        GROUP BY job_type ORDER BY count DESC
    """).fetchall()

    # Jobs by source
    jobs_by_source = conn.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs WHERE is_active = TRUE
        GROUP BY source ORDER BY count DESC
    """).fetchall()

    # Application funnel
    app_funnel = conn.execute("""
        SELECT status, COUNT(*) as count
        FROM applications
        GROUP BY status
    """).fetchall()

    # Top skills in demand
    skill_rows = conn.execute(
        "SELECT required_skills FROM job_analysis"
    ).fetchall()

    skill_counts: dict[str, int] = {}
    for row in skill_rows:
        try:
            skills = json.loads(row["required_skills"] or "[]")
            for skill in skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    # Jobs per day (last 14 days)
    daily_jobs = conn.execute("""
        SELECT DATE(date_scraped) as day, COUNT(*) as count
        FROM jobs
        WHERE date_scraped >= DATE('now', '-14 days')
        GROUP BY day ORDER BY day ASC
    """).fetchall()

    conn.close()

    return {
        "total_jobs": total_jobs,
        "total_scored": total_scored,
        "total_applications": total_apps,
        "average_score": avg_score,
        "score_distribution": {row["tier"]: row["count"] for row in score_dist},
        "jobs_by_type": {row["job_type"]: row["count"] for row in jobs_by_type},
        "jobs_by_source": {row["source"]: row["count"] for row in jobs_by_source},
        "application_funnel": {row["status"]: row["count"] for row in app_funnel},
        "top_skills": top_skills,
        "daily_jobs": [{"day": row["day"], "count": row["count"]} for row in daily_jobs],
    }


if __name__ == "__main__":
    init_db()
