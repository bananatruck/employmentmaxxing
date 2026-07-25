"""
Employmentmaxxing — Cross-Source Deduplicator
Uses fuzzy matching to detect and merge duplicate job listings across different sources.
"""

from rapidfuzz import fuzz
from database import get_connection
import json


# Similarity thresholds
TITLE_THRESHOLD = 85   # % similarity for job titles
COMPANY_THRESHOLD = 90  # % similarity for company names


def deduplicate_jobs(dry_run: bool = False) -> dict:
    """
    Find and merge duplicate job listings across sources.
    Returns stats about duplicates found and merged.
    """
    conn = get_connection()
    jobs = conn.execute(
        "SELECT id, title, company, location, source, all_sources, apply_url FROM jobs WHERE is_active = TRUE"
    ).fetchall()
    jobs = [dict(j) for j in jobs]
    conn.close()

    duplicates_found = 0
    merges = []

    # Compare all pairs (O(n²) but fine for personal use)
    seen_pairs: set[tuple[str, str]] = set()

    for i, job_a in enumerate(jobs):
        for j, job_b in enumerate(jobs):
            if i >= j:
                continue

            pair_key = tuple(sorted([job_a["id"], job_b["id"]]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Skip if same source (already deduped at insert time)
            if job_a["source"] == job_b["source"]:
                continue

            # Check company similarity
            company_sim = fuzz.ratio(
                job_a["company"].lower().strip(),
                job_b["company"].lower().strip(),
            )
            if company_sim < COMPANY_THRESHOLD:
                continue

            # Check title similarity
            title_sim = fuzz.ratio(
                job_a["title"].lower().strip(),
                job_b["title"].lower().strip(),
            )
            if title_sim < TITLE_THRESHOLD:
                continue

            # Also check URL overlap
            url_match = (
                job_a.get("apply_url", "") == job_b.get("apply_url", "")
                and job_a.get("apply_url", "") != ""
            )

            if title_sim >= TITLE_THRESHOLD or url_match:
                duplicates_found += 1
                merges.append({
                    "keep": job_a["id"],
                    "remove": job_b["id"],
                    "title_sim": title_sim,
                    "company_sim": company_sim,
                    "url_match": url_match,
                })

    if not dry_run and merges:
        _execute_merges(merges)

    return {
        "duplicates_found": duplicates_found,
        "merges_executed": len(merges) if not dry_run else 0,
        "details": merges[:20],  # Show first 20
    }


def _execute_merges(merges: list[dict]):
    """Execute merge operations: keep the first, deactivate the second."""
    conn = get_connection()

    for merge in merges:
        keep_id = merge["keep"]
        remove_id = merge["remove"]

        # Merge source lists
        keep_sources = conn.execute(
            "SELECT all_sources FROM jobs WHERE id = ?", (keep_id,)
        ).fetchone()
        remove_sources = conn.execute(
            "SELECT all_sources FROM jobs WHERE id = ?", (remove_id,)
        ).fetchone()

        if keep_sources and remove_sources:
            keep_list = json.loads(keep_sources["all_sources"] or "[]")
            remove_list = json.loads(remove_sources["all_sources"] or "[]")
            merged_sources = list(set(keep_list + remove_list))

            conn.execute(
                "UPDATE jobs SET all_sources = ? WHERE id = ?",
                (json.dumps(merged_sources), keep_id),
            )

        # Deactivate the duplicate
        conn.execute(
            "UPDATE jobs SET is_active = FALSE WHERE id = ?", (remove_id,)
        )

    conn.commit()
    conn.close()
    print(f"🔗 Merged {len(merges)} duplicate job listings")


if __name__ == "__main__":
    result = deduplicate_jobs(dry_run=True)
    print(f"Found {result['duplicates_found']} duplicates (dry run)")
    for detail in result["details"]:
        print(f"  Title sim: {detail['title_sim']}% | Company sim: {detail['company_sim']}%")
