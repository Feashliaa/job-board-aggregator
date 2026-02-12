import json
import gzip
import os
from pathlib import Path
from datetime import datetime, timezone

CHUNK_SIZE = 25_000

def load_chunks(directory):
    """Load all jobs from chunked gzip files via manifest."""
    manifest_path = Path(directory) / "jobs_manifest.json"
    if not manifest_path.exists():
        return []

    with open(manifest_path) as f:
        manifest = json.load(f)

    jobs = []
    for chunk_file in manifest["chunks"]:
        chunk_path = Path(directory) / chunk_file
        if chunk_path.exists():
            with gzip.open(chunk_path, "rt", encoding="utf-8") as f:
                jobs.extend(json.load(f))
    return jobs


def save_chunks(jobs, directory, timestamp):
    """Write chunked gzip files + manifest."""
    Path(directory).mkdir(exist_ok=True)

    # Clean old chunks
    for f in os.listdir(directory):
        if f.startswith("jobs_chunk_") and f.endswith(".json.gz"):
            os.remove(os.path.join(directory, f))

    # Sort consistently
    jobs.sort(key=lambda x: (x.get('company', '').lower(), x.get('title', '').lower()))

    chunks = [jobs[i:i + CHUNK_SIZE] for i in range(0, len(jobs), CHUNK_SIZE)]
    chunk_filenames = []

    for idx, chunk in enumerate(chunks):
        chunk_file = f"jobs_chunk_{idx}.json.gz"
        with gzip.open(os.path.join(directory, chunk_file), "wt", encoding="utf-8") as f:
            json.dump(chunk, f, indent=0)
        chunk_filenames.append(chunk_file)
        print(f"  Chunk {idx}: {len(chunk):,} jobs")

    manifest = {
        "chunks": chunk_filenames,
        "totalJobs": len(jobs),
        "last_updated": timestamp,
    }
    with open(os.path.join(directory, "jobs_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)


def merge_job_data():
    """Merge new scrape with existing data, removing stale jobs."""
    new_jobs = load_chunks("scripts/output")
    print(f"New scrape: {len(new_jobs):,} jobs")

    existing_jobs = load_chunks("data")
    print(f"Existing data: {len(existing_jobs):,} jobs")

    # Merge by URL
    merged = {}
    stale_count = 0

    for job in existing_jobs:
        url = job.get("url")
        if not url:
            continue
        scraped = job.get("scraped_at")
        if scraped:
            try:
                scraped_date = datetime.fromisoformat(scraped.replace("Z", ""))
                age_days = (datetime.now(timezone.utc) - scraped_date).days
                if age_days <= 30:
                    merged[url] = job
                else:
                    stale_count += 1
            except Exception:
                merged[url] = job
        else:
            merged[url] = job

    if stale_count > 0:
        print(f"Dropped {stale_count:,} stale jobs (>30 days old)")

    # New scrape always wins on duplicates
    for job in new_jobs:
        url = job.get("url")
        if url:
            merged[url] = job

    final_jobs = list(merged.values())
    print(f"Merged result: {len(final_jobs):,} jobs")

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    save_chunks(final_jobs, "data", timestamp)

    # Update metadata
    with open("scripts/output/metadata.json") as f:
        metadata = json.load(f)
    metadata["total_jobs"] = len(final_jobs)
    with open("data/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("Merge complete")
    return len(final_jobs)


if __name__ == "__main__":
    merge_job_data()