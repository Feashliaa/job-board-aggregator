import requests
import json
import re
import os
import gzip
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

# Flexible path handling for both local and GitHub Actions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(ROOT_DIR, "data", "greenhouse_companies.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# LOAD COMPANIES + SCRAPE GITHUB + CURATED LIST
# ============================================================


def load_existing_companies():
    """Load your Greenhouse companies from CDX scan."""
    print("\n" + "=" * 80)
    print("LOADING EXISTING COMPANIES")
    print("=" * 80 + "\n")

    try:
        with open(INPUT_FILE, "r") as f:
            companies = set(json.load(f))
        print(f"Loaded {len(companies):,} companies from {INPUT_FILE}\n")
        return companies
    except FileNotFoundError:
        print(f"File not found: {INPUT_FILE}")
        print("Make sure the path is correct!\n")
        return set()


def scrape_github_lists():
    """Scrape GitHub awesome lists to supplement your existing list."""
    print("=" * 80)
    print("SCRAPING GITHUB AWESOME LISTS (SUPPLEMENT)")
    print("=" * 80 + "\n")

    companies = set()

    repos = [
        "poteto/hiring-without-whiteboards",
        "remoteintech/remote-jobs",
        "lukasz-madon/awesome-remote-job",
    ]

    pattern = r'boards\.greenhouse\.io/([^/)\s"\'>]+)'

    for repo in repos:
        print(f"Checking {repo}...")
        for branch in ["master", "main"]:
            try:
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    matches = re.findall(pattern, response.text)
                    before = len(companies)
                    companies.update(m.lower().strip() for m in matches)
                    after = len(companies)
                    print(f"  Found {after - before} new companies")
                    break
            except Exception as e:
                continue

    print(f"\nGitHub total: {len(companies)} companies\n")
    return companies


def get_curated_companies():
    print("Adding curated tech companies...\n")

    companies = [
        "google",
        "meta",
        "amazon",
        "microsoft",
        "apple",
        "netflix",
        "openai",
        "anthropic",
        "cohere",
        "adept",
        "huggingface",
        "characterai",
        "midjourney",
        "runwayml",
        "stabilityai",
        "stripe",
        "databricks",
        "scaleai",
        "figma",
        "notion",
        "airtable",
        "webflow",
        "vercel",
        "replicate",
        "modal",
        "snowflake",
        "datadog",
        "gitlab",
        "hashicorp",
        "cockroachlabs",
        "confluent",
        "elastic",
        "mongodb",
        "redis",
        "planetscale",
        "retool",
        "gusto",
        "brex",
        "ramp",
        "rippling",
        "lattice",
        "faire",
        "plaid",
        "checkr",
        "flexport",
        "anduril",
    ]

    return set(companies)


# ============================================================
# VERIFY ACTIVE JOBS + FETCH ALL JOBS
# ============================================================


def fetch_company_jobs(slug):
    """Fetch all jobs for a company."""
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])

            if jobs:
                # Normalize job structure for frontend
                normalized = []
                for job in jobs:
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("title"),
                            "location": job.get("location", {}).get(
                                "name", "Not specified"
                            ),
                            "url": job.get("absolute_url"),
                            "absolute_url": job.get("absolute_url"),
                            "departments": [
                                d.get("name") for d in job.get("departments", [])
                            ],
                            "id": job.get("id"),
                            "updated_at": job.get("updated_at"),
                        }
                    )

                return slug, normalized

    except Exception as e:
        pass

    return slug, []


def fetch_all_jobs(companies):
    """Fetch jobs from all companies in parallel."""
    print("=" * 80)
    print(f"FETCHING JOBS FROM {len(companies):,} COMPANIES")
    print("=" * 80 + "\n")

    all_jobs = []
    active_companies = {}
    failed = 0

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {
            executor.submit(fetch_company_jobs, slug): slug for slug in companies
        }

        for i, future in enumerate(as_completed(futures), 1):
            slug, jobs = future.result()

            if jobs:
                all_jobs.extend(jobs)
                active_companies[slug] = len(jobs)
                print(f"  [{i}/{len(companies)}] {slug}: {len(jobs)} jobs")
            else:
                failed += 1
                if i % 50 == 0:
                    print(f"  [{i}/{len(companies)}] Checked... ({failed} inactive)")

    print(f"\nActive companies: {len(active_companies):,}/{len(companies):,}")
    print(f"Total jobs found: {len(all_jobs):,}\n")

    return active_companies, all_jobs


# ============================================================
# SAVE RESULTS
# ============================================================


def save_results(all_companies, active_companies, all_jobs):
    """Save all data to JSON files."""
    print("="*80)
    print("SAVING RESULTS")
    print("="*80 + "\n")
    
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Save all companies list
    companies_file = os.path.join(OUTPUT_DIR, 'all_companies.json')
    with open(companies_file, 'w') as f:
        json.dump(sorted(list(all_companies)), f, indent=2)
    print(f"All companies: {companies_file}")
    
    # Save active companies with job counts
    active_file = os.path.join(OUTPUT_DIR, 'active_companies.json')
    with open(active_file, 'w') as f:
        json.dump(active_companies, f, indent=2, sort_keys=True)
    print(f"Active companies: {active_file}")
    
    # Save all jobs (regular JSON)
    all_jobs_file = os.path.join(OUTPUT_DIR, 'all_jobs.json')
    with open(all_jobs_file, 'w') as f:
        json.dump(all_jobs, f, indent=2)
    print(f"All jobs: {all_jobs_file} ({len(all_jobs):,} jobs)")
    
    # Save compressed version for GitHub Pages
    compressed_file = os.path.join(OUTPUT_DIR, 'all_jobs.json.gz')
    with gzip.open(compressed_file, 'wt', encoding='utf-8') as f:
        json.dump(all_jobs, f)
    
    # Check compression ratio
    original_size = os.path.getsize(all_jobs_file) / (1024 * 1024)
    compressed_size = os.path.getsize(compressed_file) / (1024 * 1024)
    print(f"Compressed: {compressed_file} ({compressed_size:.1f}MB, {compressed_size/original_size*100:.1f}% of original)")
    
    # Save metadata summary
    metadata = {
        'last_updated': timestamp,
        'total_companies': len(all_companies),
        'active_companies': len(active_companies),
        'total_jobs': len(all_jobs),
        'source': 'greenhouse_api'
    }
    
    metadata_file = os.path.join(OUTPUT_DIR, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata: {metadata_file}")
    
    print()


# ============================================================
# MAIN
# ============================================================


def main():
    print("\n" + "=" * 80)
    print("JOB BOARD AGGREGATOR")
    print("Scraping all jobs from Greenhouse companies")
    print("=" * 80)

    # Load existing companies
    existing = load_existing_companies()
    if not existing:
        print("Exiting - no companies loaded!")
        return

    # Add GitHub lists
    github = scrape_github_lists()

    # Add curated companies
    curated = get_curated_companies()
    print(f"Added {len(curated)} curated companies\n")

    # Combine all
    all_companies = existing | github | curated

    print("=" * 80)
    print("TOTAL COMPANIES TO PROCESS")
    print("=" * 80)
    print(f"From CDX scan:     {len(existing):,}")
    print(f"From GitHub:       {len(github):,}")
    print(f"From curated list: {len(curated):,}")
    print(f"Total unique:      {len(all_companies):,}")
    print()

    # Fetch all jobs from all companies
    active_companies, all_jobs = fetch_all_jobs(all_companies)

    # Save everything
    save_results(all_companies, active_companies, all_jobs)

    # Final summary
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total companies:   {len(all_companies):,}")
    print(f"Active companies:  {len(active_companies):,}")
    print(f"Total jobs:        {len(all_jobs):,}")
    print(f"\nAll data saved to '{OUTPUT_DIR}/' directory")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
