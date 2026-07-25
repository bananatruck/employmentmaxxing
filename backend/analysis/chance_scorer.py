"""
Employmentmaxxing — Chance Scorer
Weighted scoring engine that gives an honest, explainable assessment
of your chances at landing each position.

No flattery. No false hope. Just honest analysis.
"""

import json
import traceback
from datetime import datetime

from google import genai
from google.genai import types

from config import settings
from analysis.skill_taxonomy import normalize_skill
from database import get_profile, get_unscored_jobs, save_chance_score


# ── Scoring Weights ─────────────────────────────────────────────────
WEIGHTS = {
    "skill_match": 0.35,       # % of required skills you have
    "education_fit": 0.15,     # Degree level + major alignment
    "experience_fit": 0.15,    # Intern/co-op targeting match
    "preferred_skills": 0.10,  # % of nice-to-have skills
    "competition": 0.10,       # Company prestige × posting age
    "location_fit": 0.10,      # Location/remote compatibility
    "ai_holistic": 0.05,       # Gemini's qualitative read
}

# Company prestige tiers (affects competition estimate)
# Higher tier = more competitive = lower score for this factor
PRESTIGE_TIERS = {
    "faang": ["google", "meta", "amazon", "apple", "netflix", "microsoft", "nvidia",
              "openai", "anthropic", "deepmind", "tesla"],
    "tier2": ["ibm", "intel", "qualcomm", "adobe", "salesforce", "palantir", "stripe",
              "airbnb", "uber", "lyft", "snap", "twitter", "x corp", "bytedance",
              "databricks", "snowflake", "splunk", "vmware", "dell", "hp"],
    "tier3": [],  # Default for all others
}


# ── Initialize Gemini client ────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _client is None and settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _calculate_skill_match(user_skills: list[str], required_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """Calculate skill match percentage. Returns (score, matched, missing)."""
    if not required_skills:
        return 0.7, [], []  # If no skills listed, give a neutral score

    user_set = {normalize_skill(s).lower() for s in user_skills}
    matched = []
    missing = []

    for skill in required_skills:
        normalized = normalize_skill(skill).lower()
        if normalized in user_set:
            matched.append(skill)
        else:
            missing.append(skill)

    score = len(matched) / len(required_skills) if required_skills else 0
    return score, matched, missing


def _calculate_education_fit(user_degree: str, user_grad_year: int, required_education: str) -> float:
    """Score education alignment."""
    if not required_education:
        return 0.8  # No requirement = good

    req_lower = required_education.lower()
    degree_lower = user_degree.lower()

    # Check if student status is acceptable
    current_year = datetime.now().year
    is_current_student = user_grad_year > current_year

    # PhD required
    if "phd" in req_lower or "doctorate" in req_lower:
        if "phd" in degree_lower:
            return 1.0
        if "master" in degree_lower or "ms" in degree_lower:
            return 0.3
        return 0.1  # BS student applying to PhD role = reach

    # Master's required
    if "master" in req_lower or "ms " in req_lower or "m.s." in req_lower:
        if "master" in degree_lower or "ms" in degree_lower:
            return 1.0
        if is_current_student and "bs" in degree_lower:
            return 0.5  # BS student can sometimes qualify
        return 0.4

    # Bachelor's / student / pursuing
    if any(kw in req_lower for kw in ["bachelor", "bs", "pursuing", "enrolled", "student"]):
        if "computer science" in degree_lower or "cs" in degree_lower:
            return 1.0
        if any(kw in degree_lower for kw in ["engineering", "math", "physics", "data"]):
            return 0.85
        return 0.6

    return 0.7  # Unclear requirement


def _calculate_experience_fit(user_grad_year: int, job_experience_level: str, years_required: int) -> float:
    """Score experience level alignment."""
    current_year = datetime.now().year
    years_until_grad = user_grad_year - current_year
    is_student = years_until_grad > 0

    level = job_experience_level.lower() if job_experience_level else ""

    if level in ["intern", "internship"]:
        return 1.0 if is_student else 0.5
    if level in ["co-op", "coop"]:
        return 1.0 if is_student else 0.4
    if level in ["new_grad", "entry", "junior"]:
        if years_until_grad <= 1:
            return 0.9  # Graduating soon
        return 0.6  # Still in school

    # Check years requirement
    if years_required == 0:
        return 0.8
    if years_required <= 1:
        return 0.7 if is_student else 0.9
    if years_required <= 2:
        return 0.4  # 2+ years for a student is a reach
    return 0.2  # 3+ years = definite reach


def _calculate_competition(company: str, days_since_posted: int = 0) -> float:
    """Estimate competition level (lower score = more competitive = harder)."""
    company_lower = company.lower().strip()

    # Determine prestige tier
    prestige_penalty = 0
    if any(c in company_lower for c in PRESTIGE_TIERS["faang"]):
        prestige_penalty = 0.4  # FAANG = very competitive
    elif any(c in company_lower for c in PRESTIGE_TIERS["tier2"]):
        prestige_penalty = 0.2
    else:
        prestige_penalty = 0.0  # Unknown/smaller = less competitive

    # Fresher postings = less competition
    freshness_bonus = 0
    if days_since_posted <= 1:
        freshness_bonus = 0.15
    elif days_since_posted <= 3:
        freshness_bonus = 0.1
    elif days_since_posted <= 7:
        freshness_bonus = 0.05

    score = 1.0 - prestige_penalty + freshness_bonus
    return max(0.1, min(1.0, score))


def _calculate_location_fit(user_locations: list[str], open_to_remote: bool,
                             job_location: str, job_is_remote: bool) -> float:
    """Score location compatibility."""
    if job_is_remote and open_to_remote:
        return 1.0

    if not job_location or job_location.lower() in ["see listing", "various", ""]:
        return 0.7  # Unknown

    job_loc_lower = job_location.lower()

    if open_to_remote and any(kw in job_loc_lower for kw in ["remote", "hybrid", "anywhere"]):
        return 0.95

    if user_locations:
        for loc in user_locations:
            if loc.lower() in job_loc_lower or job_loc_lower in loc.lower():
                return 1.0

    if not user_locations:
        return 0.7  # No preferences set = neutral

    return 0.4  # Mismatched location


def _get_ai_assessment(job: dict, profile: dict, skill_analysis: dict) -> tuple[float, str, list[str]]:
    """
    Get Gemini's holistic assessment: honest take + improvement tips.
    Returns (score_0_to_1, honest_take_text, improvement_tips_list).
    """
    client = _get_client()
    if not client:
        return 0.5, _generate_fallback_honest_take(skill_analysis), _generate_fallback_tips(skill_analysis)

    prompt = f"""You are an BRUTALLY HONEST career advisor for a CS student. No flattery.
    
Student Profile:
- Degree: {profile.get('degree', 'BS CS')} (graduating {profile.get('graduation_year', 2027)})
- Skills: {', '.join(profile.get('skills', [])[:20])}
- GPA Range: {profile.get('gpa_range', 'not specified')}
- Additional: {profile.get('additional_context', 'none')[:200]}

Job:
- Title: {job.get('title', 'Unknown')}
- Company: {job.get('company', 'Unknown')}
- Required Skills: {', '.join(skill_analysis.get('matched', []))} (MATCHED) | {', '.join(skill_analysis.get('missing', []))} (MISSING)
- Skill Match: {skill_analysis.get('match_pct', 0):.0%}
- Experience Level: {job.get('experience_level', 'unknown')}

Give an HONEST assessment. If they're underqualified, say so. If it's a great match, say so.
Be direct but not cruel. Include specific, actionable advice.

Respond ONLY with JSON:
{{
    "score": 0.0 to 1.0 (your holistic assessment),
    "honest_take": "2-3 sentence honest assessment",
    "improvement_tips": ["tip 1", "tip 2", "tip 3"]
}}"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512,
            ),
        )

        if not response or not response.text:
            return 0.5, _generate_fallback_honest_take(skill_analysis), _generate_fallback_tips(skill_analysis)

        import re
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text)
        return (
            float(result.get("score", 0.5)),
            result.get("honest_take", ""),
            result.get("improvement_tips", []),
        )

    except Exception as e:
        print(f"   ⚠️ AI assessment error: {e}")
        return 0.5, _generate_fallback_honest_take(skill_analysis), _generate_fallback_tips(skill_analysis)


def _generate_fallback_honest_take(skill_analysis: dict) -> str:
    """Generate an honest take without AI."""
    match_pct = skill_analysis.get("match_pct", 0)
    matched = skill_analysis.get("matched", [])
    missing = skill_analysis.get("missing", [])

    if match_pct >= 0.8:
        return f"Strong skill match — you have {len(matched)} of the required skills covered. This is a solid fit for your profile. Apply with confidence."
    elif match_pct >= 0.5:
        missing_str = ", ".join(missing[:3])
        return f"Decent match with room to grow. You're missing {missing_str}, but {len(matched)} matched skills gives you a fair shot. Worth applying if the role excites you."
    elif match_pct >= 0.25:
        missing_str = ", ".join(missing[:4])
        return f"This is a stretch. You're missing key skills: {missing_str}. Apply if you're genuinely interested and can demonstrate fast learning ability, but be realistic about the odds."
    else:
        return f"Significant skill gap — you match {match_pct:.0%} of requirements. Unless you have exceptional projects or experience that compensate, this is a reach application."


def _generate_fallback_tips(skill_analysis: dict) -> list[str]:
    """Generate improvement tips without AI."""
    tips = []
    missing = skill_analysis.get("missing", [])

    if missing:
        tips.append(f"Learn {missing[0]} — it's the most critical missing skill for this role")
    if len(missing) > 1:
        tips.append(f"Build a project that demonstrates {missing[1]} skills")
    tips.append("Highlight any relevant coursework or academic projects in your application")

    return tips


def _determine_verdict(score: int) -> str:
    """Determine the verdict label from overall score."""
    if score >= 81:
        return "Safety"
    elif score >= 61:
        return "Strong Match"
    elif score >= 31:
        return "Worth a Shot"
    else:
        return "Reach"


def _determine_priority(score: int, experience_fit: float) -> str:
    """Determine application priority."""
    if score >= 75 and experience_fit >= 0.8:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 35:
        return "MEDIUM"
    else:
        return "LOW"


def score_job(job: dict, profile: dict) -> dict:
    """
    Score a single job against the user's profile.
    Returns a complete score breakdown.
    """
    user_skills = profile.get("skills", [])
    required_skills_raw = job.get("required_skills", "[]")
    preferred_skills_raw = job.get("preferred_skills", "[]")

    # Parse JSON if needed
    if isinstance(required_skills_raw, str):
        try:
            required_skills = json.loads(required_skills_raw)
        except (json.JSONDecodeError, TypeError):
            required_skills = []
    else:
        required_skills = required_skills_raw or []

    if isinstance(preferred_skills_raw, str):
        try:
            preferred_skills = json.loads(preferred_skills_raw)
        except (json.JSONDecodeError, TypeError):
            preferred_skills = []
    else:
        preferred_skills = preferred_skills_raw or []

    # ── 1. Skill Match (35%) ────────────────────────────────────
    skill_pct, matched, missing = _calculate_skill_match(user_skills, required_skills)

    # ── 2. Education Fit (15%) ──────────────────────────────────
    edu_fit = _calculate_education_fit(
        profile.get("degree", "BS Computer Science"),
        profile.get("graduation_year", 2027),
        job.get("education_required", ""),
    )

    # ── 3. Experience Fit (15%) ─────────────────────────────────
    exp_fit = _calculate_experience_fit(
        profile.get("graduation_year", 2027),
        job.get("experience_level", ""),
        job.get("years_experience", 0) if isinstance(job.get("years_experience"), int) else 0,
    )

    # ── 4. Preferred Skills (10%) ───────────────────────────────
    pref_pct, pref_matched, _ = _calculate_skill_match(user_skills, preferred_skills)

    # ── 5. Competition (10%) ────────────────────────────────────
    comp_score = _calculate_competition(job.get("company", ""))

    # ── 6. Location Fit (10%) ───────────────────────────────────
    loc_fit = _calculate_location_fit(
        profile.get("preferred_locations", []),
        profile.get("open_to_remote", True),
        job.get("location", ""),
        job.get("is_remote", False),
    )

    # ── 7. AI Holistic (5%) ─────────────────────────────────────
    skill_analysis = {
        "match_pct": skill_pct,
        "matched": matched,
        "missing": missing,
    }
    ai_score, honest_take, tips = _get_ai_assessment(job, profile, skill_analysis)

    # ── Calculate Final Score ───────────────────────────────────
    raw_score = (
        skill_pct * WEIGHTS["skill_match"] +
        edu_fit * WEIGHTS["education_fit"] +
        exp_fit * WEIGHTS["experience_fit"] +
        pref_pct * WEIGHTS["preferred_skills"] +
        comp_score * WEIGHTS["competition"] +
        loc_fit * WEIGHTS["location_fit"] +
        ai_score * WEIGHTS["ai_holistic"]
    )

    overall_score = int(round(raw_score * 100))
    overall_score = max(0, min(100, overall_score))

    return {
        "overall_score": overall_score,
        "verdict": _determine_verdict(overall_score),
        "skill_match_pct": round(skill_pct * 100, 1),
        "education_fit": round(edu_fit * 100, 1),
        "experience_fit": round(exp_fit * 100, 1),
        "preferred_skill_pct": round(pref_pct * 100, 1),
        "competition_estimate": round(comp_score * 100, 1),
        "location_fit": round(loc_fit * 100, 1),
        "ai_assessment": round(ai_score * 100, 1),
        "honest_take": honest_take,
        "improvement_tips": tips,
        "apply_priority": _determine_priority(overall_score, exp_fit),
        "skill_breakdown": {
            "matched": matched,
            "missing": missing,
            "preferred_matched": pref_matched if 'pref_matched' in dir() else [],
        },
    }


def run_scoring_pipeline(limit: int = 50) -> dict:
    """
    Score all unscored jobs against the user profile.
    Returns stats.
    """
    profile = get_profile()
    if not profile or not profile.get("skills"):
        print("⚠️ No profile or skills set — please configure your profile first")
        return {"total": 0, "scored": 0, "errors": 0, "skipped_no_profile": True}

    jobs = get_unscored_jobs(limit=limit)
    stats = {"total": len(jobs), "scored": 0, "errors": 0}

    if not jobs:
        print("✅ No unscored jobs found")
        return stats

    print(f"📊 Scoring {len(jobs)} jobs against your profile...")

    for job in jobs:
        try:
            score = score_job(job, profile)
            save_chance_score(job["id"], score)
            stats["scored"] += 1

            emoji = "💎" if score["overall_score"] >= 81 else "🟢" if score["overall_score"] >= 61 else "🟡" if score["overall_score"] >= 31 else "🔴"
            print(f"   {emoji} {score['overall_score']}/100 [{score['verdict']}] {job['company']} - {job['title']}")

        except Exception as e:
            stats["errors"] += 1
            print(f"   ❌ Error scoring {job.get('company', '?')}: {e}")
            traceback.print_exc()

    print(f"✅ Scoring complete: {stats['scored']} scored / {stats['errors']} errors")
    return stats


if __name__ == "__main__":
    from database import init_db
    init_db()
    run_scoring_pipeline()
