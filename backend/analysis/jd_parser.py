"""
Employmentmaxxing — JD Parser
Uses Gemini Flash to extract structured data from raw job descriptions.
Falls back to regex-based extraction when AI is unavailable.
"""

import json
import re
import traceback
from datetime import datetime

from google import genai
from google.genai import types

from config import settings
from analysis.skill_taxonomy import normalize_skills, SKILL_ALIASES
from database import save_analysis, get_unanalyzed_jobs


# Initialize Gemini client
_client = None


def _get_client():
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None and settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


ANALYSIS_PROMPT = """You are a job description analyzer for a CS student job tracker.
Analyze the following job description and extract structured information.

IMPORTANT: Be precise and honest. Only list skills that are explicitly mentioned.
Classify experience level based on what the job actually requires.

Job Title: {title}
Company: {company}
Location: {location}

Job Description:
{description}

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
    "required_skills": ["skill1", "skill2"],
    "preferred_skills": ["skill1", "skill2"],
    "education_required": "description of education requirement",
    "years_experience": 0,
    "tech_stack": ["tech1", "tech2"],
    "visa_sponsorship": "yes" or "no" or "unknown",
    "red_flags": ["any concerns like 'unpaid' or 'excessive hours expected'"],
    "green_flags": ["positives like 'mentorship program' or 'return offer'"],
    "team_focus": "brief description of what the team works on"
}}
"""


def analyze_job_with_ai(job: dict) -> dict | None:
    """Analyze a job description using Gemini Flash."""
    client = _get_client()
    if not client:
        return None

    description = job.get("description", "")
    if not description or len(description) < 50:
        return None

    # Truncate very long descriptions to save tokens
    if len(description) > 5000:
        description = description[:5000] + "... [truncated]"

    prompt = ANALYSIS_PROMPT.format(
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", "Unknown"),
        description=description,
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for structured extraction
                max_output_tokens=1024,
            ),
        )

        if not response or not response.text:
            return None

        # Parse JSON from response
        text = response.text.strip()
        # Remove markdown code fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        analysis = json.loads(text)

        # Normalize skills
        analysis["required_skills"] = normalize_skills(analysis.get("required_skills", []))
        analysis["preferred_skills"] = normalize_skills(analysis.get("preferred_skills", []))
        analysis["tech_stack"] = normalize_skills(analysis.get("tech_stack", []))

        return analysis

    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON parse error for {job.get('company', '?')}: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Gemini error for {job.get('company', '?')}: {e}")
        traceback.print_exc()
        return None


def analyze_job_with_regex(job: dict) -> dict:
    """
    Fallback: Extract basic structured data using regex patterns.
    Less accurate but works without an API key.
    """
    description = job.get("description", "").lower()
    title = job.get("title", "").lower()
    full_text = f"{title} {description}"

    # Extract skills by matching against our taxonomy
    required_skills = []
    for alias, canonical in SKILL_ALIASES.items():
        # Use word boundary matching for short aliases
        if len(alias) <= 2:
            pattern = rf"\b{re.escape(alias)}\b"
        else:
            pattern = re.escape(alias)

        if re.search(pattern, full_text, re.IGNORECASE):
            if canonical not in required_skills:
                required_skills.append(canonical)

    # Extract years of experience
    years_exp = 0
    exp_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", full_text)
    if exp_match:
        years_exp = int(exp_match.group(1))

    # Education
    education = ""
    if any(kw in full_text for kw in ["phd", "ph.d", "doctorate"]):
        education = "PhD preferred"
    elif any(kw in full_text for kw in ["master", "ms ", "m.s."]):
        education = "Master's preferred"
    elif any(kw in full_text for kw in ["bachelor", "bs ", "b.s.", "undergraduate"]):
        education = "Bachelor's required"
    elif any(kw in full_text for kw in ["pursuing", "enrolled", "student"]):
        education = "Currently enrolled student"

    # Red/green flags
    red_flags = []
    green_flags = []

    if "unpaid" in full_text:
        red_flags.append("Unpaid position")
    if years_exp >= 3 and any(kw in title for kw in ["intern", "entry"]):
        red_flags.append(f"Requires {years_exp}+ years for an entry-level role")
    if "no visa" in full_text or "no sponsorship" in full_text:
        red_flags.append("No visa sponsorship")

    if "mentor" in full_text:
        green_flags.append("Mentorship program")
    if "return offer" in full_text:
        green_flags.append("Return offer potential")
    if any(kw in full_text for kw in ["flexible", "hybrid", "remote"]):
        green_flags.append("Flexible work arrangement")
    if "publish" in full_text or "paper" in full_text:
        green_flags.append("Research publication opportunity")

    # Visa
    visa = "unknown"
    if "sponsor" in full_text and "no" not in full_text.split("sponsor")[0][-20:]:
        visa = "yes"
    elif "no sponsor" in full_text or "no visa" in full_text:
        visa = "no"

    return {
        "required_skills": required_skills[:15],  # Cap at 15
        "preferred_skills": [],
        "education_required": education,
        "years_experience": years_exp,
        "tech_stack": required_skills[:10],
        "visa_sponsorship": visa,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "team_focus": "",
    }


def run_analysis_pipeline(limit: int = 50) -> dict:
    """
    Analyze all unanalyzed jobs.
    Uses Gemini when available, falls back to regex.
    Returns stats.
    """
    jobs = get_unanalyzed_jobs(limit=limit)
    stats = {"total": len(jobs), "ai_analyzed": 0, "regex_analyzed": 0, "errors": 0}

    if not jobs:
        print("✅ No unanalyzed jobs found")
        return stats

    print(f"🧠 Analyzing {len(jobs)} jobs...")

    for job in jobs:
        try:
            # Try AI analysis first
            analysis = analyze_job_with_ai(job)

            if analysis:
                stats["ai_analyzed"] += 1
                print(f"   🤖 AI analyzed: {job['company']} - {job['title']}")
            else:
                # Fallback to regex
                analysis = analyze_job_with_regex(job)
                stats["regex_analyzed"] += 1
                print(f"   📝 Regex analyzed: {job['company']} - {job['title']}")

            save_analysis(job["id"], analysis)

        except Exception as e:
            stats["errors"] += 1
            print(f"   ❌ Error analyzing {job.get('company', '?')}: {e}")
            traceback.print_exc()

    print(f"✅ Analysis complete: {stats['ai_analyzed']} AI + {stats['regex_analyzed']} regex / {stats['errors']} errors")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    stats = run_analysis_pipeline()
    print(stats)
