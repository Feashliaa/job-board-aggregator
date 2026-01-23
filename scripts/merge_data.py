import json
import gzip
from pathlib import Path
from datetime import datetime, timezone


def merge_job_data():
    """Merge new scrape with existing data, removing stale jobs."""

    # Load new scraped data
    new_path = Path("scripts/output/all_jobs.json.gz")
    with gzip.open(new_path, "rt", encoding="utf-8") as f:
        new_jobs = json.load(f)
    print(f"New scrape: {len(new_jobs):,} jobs")

    # Load existing data (if exists)
    existing_jobs = []
    existing_path = Path("data/all_jobs.json.gz")
    if existing_path.exists():
        with gzip.open(existing_path, "rt", encoding="utf-8") as f:
            existing_jobs = json.load(f)
        print(f"Existing data: {len(existing_jobs):,} jobs")

    # Merge by URL
    merged = {}
    stale_count = 0

    # Add existing jobs first (with age filter)
    for job in existing_jobs:
        url = job.get("absolute_url") or job.get("url")
        if not url:
            continue

        # Keep jobs scraped within last 30 days
        scraped = job.get("scraped_at")
        if scraped:
            try:
                scraped_date = datetime.fromisoformat(scraped.replace("Z", ""))
                now = datetime.now(timezone.utc)
                age_days = (now - scraped_date).days

                if age_days <= 30:
                    merged[url] = job
                else:
                    stale_count += 1
            except Exception:
                # If date parsing fails, keep the job
                merged[url] = job
        else:
            # No scraped_at field, keep it
            merged[url] = job

    if stale_count > 0:
        print(f"Dropped {stale_count:,} stale jobs (>30 days old)")

    # Add/update with new scrape (always wins on duplicates)
    for job in new_jobs:
        url = job.get("absolute_url") or job.get("url")
        if url:
            merged[url] = job

    # Convert to list
    final_jobs = list(merged.values())
    print(f"Merged result: {len(final_jobs):,} jobs")

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    # Save merged data
    with gzip.open("data/all_jobs.json.gz", "wt", encoding="utf-8") as f:
        json.dump(final_jobs, f)

    # Update metadata
    with open("scripts/output/metadata.json", "r") as f:
        metadata = json.load(f)

    metadata["total_jobs"] = len(final_jobs)

    with open("data/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("Merge complete")
    return len(final_jobs)


if __name__ == "__main__":
    merge_job_data()
