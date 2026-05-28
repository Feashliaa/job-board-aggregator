import requests
import json
import random
import time
import re
import os
import gzip
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote
from geolocation import build_lookup, lookup_location

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

LOCATIONS_FILE = os.path.join(ROOT_DIR, "data", "locations.json")


OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# GEOLOCATION LOOKUP (loaded once, shared across all workers)
# ============================================================

print("Loading location lookup from locations.json...")
LOCATION_MAPS = build_lookup(LOCATIONS_FILE)
print(f"  {len(LOCATION_MAPS['city']):,} city-only entries loaded")


def enrich_location(location_str):
    """Resolve a location string to (remote, coords). Safe to call from worker threads."""
    result = lookup_location(location_str, LOCATION_MAPS)
    return result["remote"], result["coords"]


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

USER_AGENTS = [
    # Chrome 144 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    # Chrome 144 - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    # Chrome 144 - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    # Firefox 147 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
    # Firefox 147 - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    # Firefox 147 - Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    # Safari 26 - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15",
    # Edge 144 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
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

SOURCE_TYPE = "automated"


def get_job_metadata():
    """Generate consistent metadata for each job."""
    return {
        "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": SOURCE_TYPE,
    }


def fetch_company_jobs_greenhouse(slug):
    """Fetch all jobs for a company."""
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])

            if jobs:
                # Normalize job structure for frontend
                normalized = []
                for job in jobs:
                    location = job.get("location", {}).get("name", "Not specified")
                    remote, coords = enrich_location(location)
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("title"),
                            "location": location,
                            "remote": remote,
                            "coords": coords,
                            "url": job.get("absolute_url"),
                            "absolute_url": job.get("absolute_url"),
                            "departments": [
                                d.get("name") for d in job.get("departments", [])
                            ],
                            "id": job.get("id"),
                            "updated_at": job.get("updated_at"),
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "Greenhouse",
                            "skill_level": job_tier_classification(
                                job.get("title", "")
                            ),
                            **get_job_metadata(),
                        }
                    )

                return slug, normalized, response.status_code

        return slug, [], response.status_code  # got a response, just not 200

    except Exception as e:
        print(f"Error fetching Greenhouse for {slug}: {e}")
    return slug, [], None


def fetch_company_jobs_ashby(slug):
    try:
        url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": slug},
            "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName } } }",
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": random.choice(USER_AGENTS),
        }

        # Jitter before request to spread out concurrent workers
        time.sleep(random.uniform(0.5, 2.0))

        max_retries = 2
        for attempt in range(max_retries + 1):
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                break
            elif response.status_code in (429, 503, 502):
                if attempt < max_retries:
                    backoff = (2**attempt) + random.uniform(0.5, 1.5)
                    print(
                        f"  Ashby {slug}: {response.status_code}, retrying in {backoff:.1f}s"
                    )
                    time.sleep(backoff)
                    headers["User-Agent"] = random.choice(USER_AGENTS)
                    continue
            # Non-retryable status
            return slug, [], response.status_code

        if response.status_code != 200:
            return slug, [], response.status_code

        data = response.json()
        jobs = (data.get("data") or {}).get("jobBoard") or {}
        jobs = jobs.get("jobPostings") or []

        if jobs:
            normalized = []
            for job in jobs:
                normalized.append(
                    {
                        "company": slug,
                        "company_slug": slug,
                        "title": job.get("title", ""),
                        "location": job.get("locationName", "Not specified")[:50],
                        "url": f"https://jobs.ashbyhq.com/{slug}/{job.get('id')}",
                        "is_recruiter": is_recruiter_company(slug),
                        "ats": "Ashby",
                        "skill_level": job_tier_classification(job.get("title", "")),
                        **get_job_metadata(),
                    }
                )
            return slug, normalized, response.status_code

        return slug, [], response.status_code  # got a response, just not 200

    except Exception as e:
        print(f"Error fetching Ashby for {slug}: {e}")
    return slug, [], None


def fetch_company_jobs_bamboohr(slug):
    """https://{slug}.bamboohr.com/careers
    https://{slug}.bamboohr.com/careers/list

    """
    url = f"https://{slug}.bamboohr.com/careers/list"

    time.sleep(random.uniform(0.5, 2.0))

    max_retries = 2
    for attempt in range(max_retries + 1):
        headers = {
            "Accept": "application/json",
            "User-Agent": random.choice(USER_AGENTS),
        }

        try:
            response = requests.get(url, timeout=30, headers=headers)

            if response.status_code == 200:
                if "application/json" not in response.headers.get("Content-Type", ""):
                    return slug, [], 404

                data = response.json()
                jobs = data.get("result", [])

                if jobs:
                    normalized = []
                    for job in jobs:
                        loc = job.get("location") or {}
                        if isinstance(loc, dict):
                            city = loc.get("city", "")
                            state = loc.get("state", "")
                            location = (
                                ", ".join(filter(None, [city, state])) or "Not specified"
                            )
                        else:
                            location = str(loc) if loc else "Not specified"

                        remote, coords = enrich_location(location)
                        normalized.append(
                            {
                                "company": slug,
                                "company_slug": slug,
                                "title": job.get("jobOpeningName"),
                                "location": location[:50],
                                "remote": remote,
                                "coords": coords,
                                "url": f"https://{slug}.bamboohr.com/careers/{job.get('id')}",
                                "is_recruiter": is_recruiter_company(slug),
                                "ats": "BambooHR",
                                "skill_level": job_tier_classification(
                                    job.get("jobOpeningName", "")
                                ),
                                **get_job_metadata(),
                            }
                        )
                    return slug, normalized, response.status_code

                return slug, [], response.status_code

            if response.status_code in (429, 503, 502):
                if attempt < max_retries:
                    backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                    time.sleep(backoff)
                    continue

            return slug, [], response.status_code

        except requests.exceptions.SSLError:
            if attempt < max_retries:
                time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
                continue
            return slug, [], None
        except Exception as e:
            print(f"Error fetching BambooHR for {slug}: {e}")
            return slug, [], None

    return slug, [], None


def fetch_company_jobs_lever(slug):
    """https://api.lever.co/v0/postings/{slug}"""

    try:
        url = f"https://api.lever.co/v0/postings/{slug}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            jobs = response.json()

            if jobs:
                normalized = []
                for job in jobs:
                    categories = job.get("categories", {})
                    location = categories.get("location", "Not specified")[:50]
                    remote, coords = enrich_location(location)
                    normalized.append(
                        {
                            "company": slug,
                            "company_slug": slug,
                            "title": job.get("text"),
                            "location": location,
                            "remote": remote,
                            "coords": coords,
                            "url": job.get("hostedUrl"),
                            "is_recruiter": is_recruiter_company(slug),
                            "ats": "Lever",
                            "skill_level": job_tier_classification(job.get("text", "")),
                            **get_job_metadata(),
                        }
                    )
                return slug, normalized, response.status_code
        return slug, [], response.status_code  # got a response, just not 200
    except Exception as e:
        print(f"Error fetching Lever for {slug}: {e}")
    return slug, [], None


def fetch_company_jobs_workday(slug):
    """
    slug format: "company|wd#|site_id" e.g. "kohls|wd1|kohlscareers"
    url: https://{company}.wd{num}.myworkdayjobs.com/wday/cxs/{company}/{site_id}/jobs
    """

    try:
        parts = slug.split("|")
        if len(parts) != 3:
            return slug, [], None

        company, wd, site_id = parts
        wd_num = wd.replace("wd", "")

        base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
        api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": random.choice(USER_AGENTS),
            "Origin": base_url,
            "Referer": f"{base_url}/{site_id}",
        }

        normalized = []
        offset = 0
        limit = 20
        retries = 0
        max_retries = 2
        observed_total = None

        while True:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }

            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                if retries < max_retries:
                    retries += 1
                    time.sleep(random.uniform(2.0, 4.0))
                    continue
                break

            data = response.json()
            jobs = data.get("jobPostings", [])
            total = data.get("total", 0)

            # Detect silent blocking / truncation
            if observed_total is None:
                observed_total = total
            elif total != observed_total:
                # Workday sometimes lies mid-pagination when blocking
                break

            if not jobs:
                break

            for job in jobs:
                job_path = job.get("externalPath", "")
                location = (job.get("locationsText") or "Not specified")[:50]
                remote, coords = enrich_location(location)
                normalized.append(
                    {
                        "company": company,
                        "company_slug": slug,
                        "title": job.get("title"),
                        "location": location,
                        "remote": remote,
                        "coords": coords,
                        "url": f"{base_url}/{site_id}{job_path}",
                        "is_recruiter": is_recruiter_company(company),
                        "ats": "Workday",
                        "skill_level": job_tier_classification(job.get("title", "")),
                        **get_job_metadata(),
                    }
                )

            offset += limit

            if offset >= total:
                break

            # Jitter between pages (critical)
            time.sleep(random.uniform(0.3, 1.0))

        return slug, normalized, response.status_code

    except Exception:
        return slug, [], None


def fetch_company_jobs_icims(slug):
    """
    https://careers-{slug}.icims.com/sitemap.xml

    Sitemap contains job URLs like:
        https://careers-{slug}.icims.com/jobs/9620/financial-service-representative/job

    Title extracted from URL path. Location not available via sitemap. Might look into fetching individual job pages for location,
    but that would be a lot more requests so skipping for now.
    """

    sitemap_url = f"https://careers-{slug}.icims.com/sitemap.xml"
    headers = {
        "Accept": "application/xml",
        "User-Agent": random.choice(USER_AGENTS),
    }

    try:
        resp = requests.get(sitemap_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return slug, [], resp.status_code

        root = ET.fromstring(resp.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        normalized = []
        for loc in root.findall(".//s:url/s:loc", ns):
            job_url = loc.text.strip() if loc.text else ""
            if (
                not job_url
                or "/jobs/" not in job_url
                or job_url.endswith("/jobs/intro")
            ):
                continue

            path = job_url.split("/jobs/")[-1]
            parts = path.split("/")
            if len(parts) >= 2:
                title = unquote(parts[1]).replace("-", " ").strip().title()
            else:
                continue
            
            remote, coords = False, None
            normalized.append(
                {
                    "company": slug,
                    "company_slug": slug,
                    "title": title,
                    "location": "Not specified",
                    "remote": remote,
                    "coords": coords,
                    "url": job_url,
                    "is_recruiter": is_recruiter_company(slug),
                    "ats": "iCIMS",
                    "skill_level": job_tier_classification(title),
                    **get_job_metadata(),
                }
            )

        return slug, normalized, resp.status_code

    except Exception as e:
        print(f"Error fetching iCIMS for {slug}: {e}")
        return slug, [], None


# TODO - Add Workable


def fetch_all_jobs(companies, fetcher, platform="ATS"):
    """Fetch jobs from all companies in parallel."""
    print("=" * 80)
    print(f"FETCHING JOBS FROM {len(companies):,} COMPANIES FROM PLATFORM: {platform}")
    print("=" * 80 + "\n")

    platform_lower = platform.lower()

    # Skip known dead slugs
    dead_slugs = load_dead_slugs(platform_lower)
    live_companies = [s for s in companies if s not in dead_slugs]
    if dead_slugs:
        print(f"  Skipping {len(dead_slugs):,} known dead slugs")
        print(f"  Checking {len(live_companies):,} potentially active companies\n")

    all_jobs = []
    active_companies = {}
    failed = 0
    new_dead = set()

    MAX_WORKERS = {
        "bamboohr": 10,
        "greenhouse": 30,
        "ashby": 5,
        "lever": 30,
        "workday": 50,
        "icims": 30,
    }

    max_workers = MAX_WORKERS.get(platform_lower, 30)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetcher, slug): slug for slug in live_companies}

        for i, future in enumerate(as_completed(futures), 1):

            # fetcher returns slug, jobs, status_code (if implemented)
            slug, jobs, status_code = future.result()

            if jobs:
                all_jobs.extend(jobs)
                active_companies[slug] = len(jobs)
                print(f"  [{i}/{len(live_companies)}] {slug}: {len(jobs)} jobs")
            else:
                failed += 1
                # Only cache permanent failures
                if status_code in (404, 410):
                    new_dead.add(slug)
                if i % 50 == 0:
                    print(
                        f"  [{i}/{len(live_companies)}] Checked... ({failed} inactive)"
                    )

    # Update dead slug cache
    if new_dead:
        all_dead = dead_slugs | new_dead
        save_dead_slugs(platform_lower, all_dead)

    print(f"\nDETAILED STATS FOR {platform}:")
    print(f"  Companies checked: {len(live_companies)}")
    print(f"  Companies with jobs: {len(active_companies)}")
    print(f"  Failed/empty: {failed}")
    print(f"  Newly dead: {len(new_dead)}")
    print(f"  Total jobs: {len(all_jobs)}")

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
    skipped_reasons = {"no_title": 0, "no_url": 0, "no_company": 0}

    for job in jobs:
        title = (job.get("title") or "").strip().lower()
        url = job.get("url") or job.get("absolute_url")
        company = job.get("company") or job.get("company_slug")

        # Skip jobs with invalid titles
        if not title or title in ["not specified", "n/a", "unknown", ""]:
            skipped_reasons["no_title"] += 1
            continue

        # Skip jobs without URLs
        if not url:
            skipped_reasons["no_url"] += 1
            continue

        # Skip jobs without company info
        if not company:
            skipped_reasons["no_company"] += 1
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


def job_tier_classification(title):
    """Classify job tier using weighted keyword scoring."""

    title_lower = title.lower()
    score = 0

    # Weights: positive = senior, negative = junior
    keywords = {
        # Strong senior indicators
        r"\b(?:chief|cto|ceo|cfo|vp|vice president|director)\b": 50,  # chief, cto, ceo, cfo, vp, vice president, director
        r"\b(?:principal|distinguished|fellow)\b": 40,  # principal, distinguished, fellow
        r"\b(?:staff|lead|head of)\b": 30,  # staff, lead, head of
        r"\b(?:senior|sr\.?)\b": 20,  # senior, sr.
        r"\b(?:architect|manager)\b": 15,  # architect, manager
        r"\b(?:iii|iv|v|vi)\b": 15,  # Roman numerals, i.e. III, IV, V, VI for levels
        r"\blevel\s*[4-9]\b": 15,  # e.g. Level 4, Level 5, Level 6, Level 7, Level 8, Level 9
        r"\bengr?\s*[4-6]\b": 15,  # e.g. Engr 4, Engr 5, Engr 6
        r"\b(?:counsel|of\s*counsel)\b": 20,  # senior attorney
        r"\b(?:attending|charge)\b": 20,  # attending physician, charge nurse = senior
        # Weak senior indicators
        r"\b(?:ii|2)\b": 5,  # level II or 2
        r"\blevel\s*3\b": 5,  # level 3
        # Entry-level indicators
        r"\b(?:associate)\b": -10,  # associate
        r"\b(?:junior|jr\.?)\b": -20,  # junior, jr.
        r"\b(?:trainee|graduate|new\s*grad)\b": -25,  # trainee, graduate, new grad
        r"\bentry[\s-]?level\b": -25,  # entry-level
        r"\b(?:i|1)\b(?!\s*-|\d)": -15,  # "I" or "1" but not "1-2" or "10"
        r"\b(?:trainee|graduate|new\s*grad)\b": -25,  # trainee, graduate, new grad
        r"\b(?:paralegal|clerk)\b": -15,  # entry-level legal
        r"\b(?:resident|clinical\s*fellow)\b": -15,  # medical residency = entry-ish
        r"\b(?:aide|assistant|tech)\b": -10,  # nurse aide, medical assistant
        # Intern (heavily weighted)
        r"\bintern(?:ship)?\b": -100,  # intern or internship
    }

    # Calculate score
    for pattern, weight in keywords.items():
        if re.search(pattern, title_lower):  # if pattern matches
            score += weight

    # tiers
    if score <= -50:
        return "intern"
    elif score <= -5:
        return "entry"
    elif score >= 15:
        return "senior"
    else:
        return "mid"


# ============================================================
# DEAD SLUG CACHE
# ============================================================

DEAD_SLUG_DIR = os.path.join(ROOT_DIR, "data", "dead_slugs")
os.makedirs(DEAD_SLUG_DIR, exist_ok=True)


def load_dead_slugs(platform):
    """Load cached dead slugs for a platform."""
    filepath = os.path.join(DEAD_SLUG_DIR, f"{platform}.json")
    if not os.path.exists(filepath):
        return set()
    try:
        with open(filepath, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def save_dead_slugs(platform, slugs):
    """Save dead slugs for a platform."""
    filepath = os.path.join(DEAD_SLUG_DIR, f"{platform}.json")
    with open(filepath, "w") as f:
        json.dump(sorted(slugs), f, indent=2)
    print(f"  Cached {len(slugs):,} dead slugs for {platform}")


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
    
    # Load salary lookup once
    salary_lookup_path = os.path.join(ROOT_DIR, "data", "salary", "salary_lookup.json")
    salary_lookup = {}
    salary_fallback = {}
    if os.path.exists(salary_lookup_path):
        with open(salary_lookup_path) as f:
            data = json.load(f)
            salary_lookup = data.get("primary", {})
            salary_fallback = data.get("fallback", {})
        print(f"Loaded {len(salary_lookup):,} salary entries")

    # Enrich jobs with salary data
    for job in all_jobs:
        company = (job.get("company") or "").lower().strip()
        title = (job.get("title") or "").lower().strip()
        level = job.get("skill_level", "mid")
        
        primary_key = f"{company}|{title}|{level}"
        fallback_key = f"{title}|{level}"
        
        job["salary"] = (
            salary_lookup.get(primary_key) or
            salary_fallback.get(fallback_key)
        )

    # Save all jobs
    all_jobs_file = os.path.join(OUTPUT_DIR, "all_jobs.json")
    with open(all_jobs_file, "w") as f:
        json.dump(all_jobs, f, indent=2)
    print(f"All jobs: {all_jobs_file} ({len(all_jobs):,} jobs)")

    # Build slim version for frontend
    FRONTEND_FIELDS = {
        "title",
        "company",
        "location",
        "url",
        "ats",
        "skill_level",
        "is_recruiter",
        "workplaceType",
        "scraped_at",
        "remote",
        "coords",
        "salary"
    }

    slim_jobs = [
        {k: job.get(k) for k in FRONTEND_FIELDS if k in job} for job in all_jobs
    ]

    # Pre-sort by company name for better frontend caching
    slim_jobs.sort(
        key=lambda x: (x.get("company", "").lower(), x.get("title", "").lower())
    )

    # Chunks go in a subdirectory to keep the output folder organized
    chunks_dir = os.path.join(OUTPUT_DIR, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    # Remove old chunk files to prevent confusion and save space
    for old_chunk in os.listdir(chunks_dir):
        if old_chunk.startswith("jobs_chunk_") and old_chunk.endswith(".json.gz"):
            os.remove(os.path.join(chunks_dir, old_chunk))

    # Split into chunks of ~25k for frontend loading (with gzip compression)
    CHUNK_SIZE = 25_000

    chunks = [
        slim_jobs[i : i + CHUNK_SIZE] for i in range(0, len(slim_jobs), CHUNK_SIZE)
    ]

    chunk_filenames = []
    for idx, chunk in enumerate(chunks):
        chunk_file = os.path.join(chunks_dir, f"jobs_chunk_{idx}.json.gz")
        with gzip.open(chunk_file, "wt", encoding="utf-8") as f:
            json.dump(chunk, f, indent=0)
        chunk_filenames.append(f"jobs_chunk_{idx}.json.gz")
        size_mb = os.path.getsize(chunk_file) / (1024 * 1024)
        print(f"  Chunk {idx}: {len(chunk):,} jobs ({size_mb:.1f}MB)")

    # Manifest so the frontend knows what to load
    manifest = {
        "chunks": chunk_filenames,
        "totalJobs": len(slim_jobs),
        "last_updated": timestamp,
    }
    manifest_file = os.path.join(chunks_dir, "jobs_manifest.json")
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    recruiter_jobs = sum(1 for job in all_jobs if job.get("is_recruiter"))

    # Save metadata summary
    metadata = {
        "last_updated": timestamp,
        "total_companies": len(all_companies),
        "active_companies": len(active_companies),
        "total_jobs": len(all_jobs),
        "recruiter_jobs": recruiter_jobs,
        "source_type": SOURCE_TYPE,
        "platforms": "greenhouse_api, ashby_api, bamboohr_api, lever_api, workday_api, icims_sitemap",
    }

    metadata_file = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata: {metadata_file}")

    print()


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
    icims_companies = load_companies(ICIMS_FILE)

    if (
        not greenhouse_companies
        and not ashby_companies
        and not bamboohr_companies
        and not lever_companies
        and not workday_companies
        and not icims_companies
    ):
        print("Exiting - no companies loaded!")
        return

    # Define all platform jobs
    platforms = [
        (greenhouse_companies, fetch_company_jobs_greenhouse, "GREENHOUSE"),
        (ashby_companies, fetch_company_jobs_ashby, "ASHBY"),
        (bamboohr_companies, fetch_company_jobs_bamboohr, "BAMBOOHR"),
        (lever_companies, fetch_company_jobs_lever, "LEVER"),
        (workday_companies, fetch_company_jobs_workday, "WORKDAY"),
        (icims_companies, fetch_company_jobs_icims, "iCIMS"),
    ]

    # Run all platforms concurrently
    all_active_companies = {}
    all_jobs = []

    with ThreadPoolExecutor(max_workers=len(platforms)) as platform_executor:
        futures = {
            platform_executor.submit(fetch_all_jobs, companies, fetcher, name): name
            for companies, fetcher, name in platforms
        }

        for future in as_completed(futures):
            name = futures[future]
            active, jobs = future.result()
            all_active_companies.update(active)
            all_jobs.extend(jobs)
            print(
                f"\n  >>> {name} COMPLETE: {len(active):,} active, {len(jobs):,} jobs <<<\n"
            )

    # Combine all company sets for total count
    all_companies = (
        greenhouse_companies
        | ashby_companies
        | bamboohr_companies
        | lever_companies
        | workday_companies
        | icims_companies
    )

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
    parser = argparse.ArgumentParser(description="Job Board Aggregator Scraper")
    parser.add_argument(
        "--source",
        choices=["automated", "manual"],
        default="automated",
        help="Source type: automated (GitHub Actions) or manual (local run)",
    )

    args = parser.parse_args()
    SOURCE_TYPE = args.source

    print(f"\nRunning in {SOURCE_TYPE.upper()} mode\n")

    main()