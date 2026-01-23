import requests
import json
import re
import os
import gzip
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
GREENHOUSE_FILE = os.path.join(ROOT_DIR, "data", "greenhouse_companies.json")
ASHBY_FILE = os.path.join(ROOT_DIR, "data", "ashby_companies.json")
BAMBOOHR_FILE = os.path.join(ROOT_DIR, "data", "bamboohr_companies.json")
WORKDAY_FILE = os.path.join(ROOT_DIR, "data", "workday_companies.json")
LEVER_FILE = os.path.join(ROOT_DIR, "data", "lever_companies.json")

ICIMS_FILE = os.path.join(ROOT_DIR, "data", "icims_companies.json")

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RECRUITER_TERMS = [
    "recruit",
    "recruiting",
    "recruiter",
    "staffing",
    "staff",
    "talent",
    "talenthub",
    "talentgroup",
    "solutions",
    "consulting",
    "placement",
    "search",
    "resources",
    "agency",
]


# ============================================================
# LOAD COMPANIES
# ============================================================


def load_companies(filepath):
    """Load companies from JSON file."""
    try:
        with open(filepath, "r") as f:
            companies = set(json.load(f))
        print(f"Loaded {len(companies):,} companies from {filepath}")
        return companies
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return set()


# ============================================================
# VERIFY ACTIVE JOBS + FETCH ALL JOBS
# ============================================================

# API requests for testing in browser console
"""
fetch("https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    operationName: "ApiJobBoardWithTeams",
    variables: {organizationHostedJobsPageName: "zip"},
    query: "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName } } }"
  })
}).then(r => r.json()).then(console.log)

fetch("https://{slug}.bamboohr.com/careers/list"){
    method: "GET",
    headers: {"Content-Type": "application/json"},
}.then(r => r.json()).then(console.log)

}
"""


def fetch_company_jobs_greenhouse(slug):
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
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "Greenhouse",
                        }
                    )

                return slug, normalized

    except Exception as e:
        pass

    return slug, []

def fetch_company_jobs_ashby(slug):
    try:
        url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": slug},
            "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName } } }",
        }

        response = requests.post(url, json=payload, timeout=15)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("data", {}).get("jobBoard", {}).get("jobPostings", [])

            if jobs:
                normalized = []
                for job in jobs:
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("title"),
                            "location": job.get("locationName", "Not specified"),
                            "url": f"https://jobs.ashbyhq.com/{slug}/jobs/{job.get('id')}",
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "Ashby",
                        }
                    )
                return slug, normalized
    except Exception as e:
        pass
    return slug, []

def fetch_company_jobs_bamboohr(slug):
    """https://{slug}.bamboohr.com/careers
    https://{slug}.bamboohr.com/careers/list

    """

    try:
        url = f"https://{slug}.bamboohr.com/careers/list"
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("result", [])

            if jobs:
                normalized = []
                for job in jobs:
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("jobOpeningName"),
                            "location": job.get("location", "Not specified"),
                            "url": f"https://{slug}.bamboohr.com/careers/view/{job.get('id')}",
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "BambooHR",
                        }
                    )
                return slug, normalized
    except Exception as e:
        pass
    return slug, []

def fetch_company_jobs_lever(slug):
    """https://api.lever.co/v0/postings/{slug}"""

    try:
        url = f"https://api.lever.co/v0/postings/{slug}"
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            jobs = response.json()

            if jobs:
                normalized = []
                for job in jobs:
                    categories = job.get("categories", {})
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("text"),
                            "location": categories.get("location", "Not specified"),
                            "url": job.get("hostedUrl"),
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "Lever",
                        }
                    )
                return slug, normalized
    except Exception as e:
        pass
    return slug, []

def fetch_company_jobs_workday(slug):
    """
    slug format: "company|wd#|site_id" e.g. "kohls|wd1|kohlscareers"
    url: https://{company}.wd{num}.myworkdayjobs.com/wday/cxs/{company}/{site_id}/jobs
    """

    try:
        parts = slug.split("|")
        if len(parts) != 3:
            return slug, []

        company, wd, site_id = parts
        wd_num = wd.replace("wd", "")

        base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
        api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        normalized = []
        offset = 0
        limit = 20

        while True:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=15)

            if response.status_code != 200:
                break

            data = response.json()
            jobs = data.get("jobPostings", [])
            total = data.get("total", 0)

            for job in jobs:
                job_path = job.get("externalPath", "")
                normalized.append(
                    {
                        "company": company,
                        "company_slug": slug,
                        "title": job.get("title"),
                        "location": job.get("locationsText", "Not specified"),
                        "url": f"{base_url}{job_path}",
                        "is_recruiter": is_recruiter_company(company),
                        "ats": "Workday",
                    }
                )

            offset += limit
            if offset >= total:
                break

        return slug, normalized

    except Exception as e:
        pass
    return slug, []

def fetch_company_jobs_icims(slug):
    
    # URL: https://careers-{company}.icims.com/jobs/search?ss

    
    return slug, []

def fetch_all_jobs(companies, fetcher, platform="ATS"):
    """Fetch jobs from all companies in parallel."""
    print("=" * 80)
    print(f"FETCHING JOBS FROM {len(companies):,} COMPANIES FROM PLATFORM: {platform}")
    print("=" * 80 + "\n")

    all_jobs = []
    active_companies = {}
    failed = 0

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(fetcher, slug): slug for slug in companies}

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
# Helper Functions
# ============================================================


def is_recruiter_company(slug):
    slug = slug.lower()

    # Keyword-based detection
    if any(term in slug for term in RECRUITER_TERMS):
        return True

    return False



def clean_job_data(jobs):
    """Remove invalid/useless job entries."""
    cleaned = []
    skipped_reasons = {'no_title': 0, 'no_url': 0, 'no_company': 0}
    
    for job in jobs:
        title = (job.get('title') or '').strip().lower()
        url = job.get('url') or job.get('absolute_url')
        company = job.get('company') or job.get('company_slug')
        
        # Skip jobs with invalid titles
        if not title or title in ['not specified', 'n/a', 'unknown', '']:
            skipped_reasons['no_title'] += 1
            continue
        
        # Skip jobs without URLs
        if not url:
            skipped_reasons['no_url'] += 1
            continue
            
        # Skip jobs without company info
        if not company:
            skipped_reasons['no_company'] += 1
            continue
            
        cleaned.append(job)
    
    # Print summary
    total_skipped = sum(skipped_reasons.values())
    if total_skipped > 0:
        print(f"\n  Skipped {total_skipped:,} invalid jobs:")
        for reason, count in skipped_reasons.items():
            if count > 0:
                print(f"    - {reason.replace('_', ' ').title()}: {count:,}")
    
    return cleaned

# ============================================================
# SAVE RESULTS
# ============================================================


def save_results(all_companies, active_companies, all_jobs):
    """Save all data to JSON files."""
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80 + "\n")
    
    original_count = len(all_jobs)
    all_jobs = clean_job_data(all_jobs)
    cleaned_count = original_count - len(all_jobs)
    print(f"Removed {cleaned_count:,} invalid jobs (blank/not specified titles)")

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Save all companies list
    companies_file = os.path.join(OUTPUT_DIR, "all_companies.json")
    with open(companies_file, "w") as f:
        json.dump(sorted(list(all_companies)), f, indent=2)
    print(f"All companies: {companies_file}")

    # Save active companies with job counts
    active_file = os.path.join(OUTPUT_DIR, "active_companies.json")
    with open(active_file, "w") as f:
        json.dump(active_companies, f, indent=2, sort_keys=True)
    print(f"Active companies: {active_file}")

    # Save all jobs
    all_jobs_file = os.path.join(OUTPUT_DIR, "all_jobs.json")
    with open(all_jobs_file, "w") as f:
        json.dump(all_jobs, f, indent=2)
    print(f"All jobs: {all_jobs_file} ({len(all_jobs):,} jobs)")

    # Save compressed version for GitHub Pages
    compressed_file = os.path.join(OUTPUT_DIR, "all_jobs.json.gz")
    with gzip.open(compressed_file, "wt", encoding="utf-8") as f:
        json.dump(all_jobs, f)

    # Check compression ratio
    original_size = os.path.getsize(all_jobs_file) / (1024 * 1024)
    compressed_size = os.path.getsize(compressed_file) / (1024 * 1024)
    print(
        f"Compressed: {compressed_file} ({compressed_size:.1f}MB, {compressed_size/original_size*100:.1f}% of original)"
    )

    recruiter_jobs = sum(1 for job in all_jobs if job.get("is_recruiter"))

    # Save metadata summary
    metadata = {
        "last_updated": timestamp,
        "total_companies": len(all_companies),
        "active_companies": len(active_companies),
        "total_jobs": len(all_jobs),
        "recruiter_jobs": recruiter_jobs,
        "source": "greenhouse_api, ashby_api, bamboohr_api, lever_api, workday_api",
    }

    metadata_file = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata: {metadata_file}")

    print()


# ============================================================
# MAIN
# ============================================================


def main():
    print("\n" + "=" * 80)
    print("JOB BOARD AGGREGATOR")
    print("Scraping all jobs from ATS companies")
    print("=" * 80)

    # Load existing companies
    greenhouse_companies = load_companies(GREENHOUSE_FILE)
    ashby_companies = load_companies(ASHBY_FILE)
    bamboohr_companies = load_companies(BAMBOOHR_FILE)
    lever_companies = load_companies(LEVER_FILE)
    workday_companies = load_companies(WORKDAY_FILE)
    
    
    if (
        not greenhouse_companies
        and not ashby_companies
        and not bamboohr_companies
        and not lever_companies
        and not workday_companies
    ):
        print("Exiting - no companies loaded!")
        return

    # Fetch from all sources
    active_greenhouse, jobs_greenhouse = fetch_all_jobs(
        greenhouse_companies, fetch_company_jobs_greenhouse, "GREENHOUSE"
    )
    active_ashby, jobs_ashby = fetch_all_jobs(
        ashby_companies, fetch_company_jobs_ashby, "ASHBY"
    )

    (
        active_bamboohy,
        jobs_bamboohr,
    ) = fetch_all_jobs(bamboohr_companies, fetch_company_jobs_bamboohr, "BAMBOOHR")

    active_lever, jobs_lever = fetch_all_jobs(
        lever_companies, fetch_company_jobs_lever, "LEVER"
    )

    active_workday, jobs_workday = fetch_all_jobs(
        workday_companies, fetch_company_jobs_workday, "WORKDAY"
    )

    # Combine results
    all_companies = (
        greenhouse_companies
        | ashby_companies
        | bamboohr_companies
        | lever_companies
        | workday_companies
    )
    all_active_companies = {
        **active_greenhouse,
        **active_ashby,
        **active_bamboohy,
        **active_lever,
        **active_workday,
    }
    all_jobs = jobs_greenhouse + jobs_ashby + jobs_bamboohr + jobs_lever + jobs_workday

    save_results(all_companies, all_active_companies, all_jobs)

    # Final summary
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total companies:   {len(all_companies):,}")
    print(f"Active companies:  {len(all_active_companies):,}")
    print(f"Total jobs:        {len(all_jobs):,}")
    print(f"\nAll data saved to '{OUTPUT_DIR}/' directory")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
