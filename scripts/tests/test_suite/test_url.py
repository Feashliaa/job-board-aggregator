import sys
import time
import random
import requests
import os

from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2])
)

 
from scraper import (
    fetch_company_jobs_greenhouse,
    fetch_company_jobs_ashby,
    fetch_company_jobs_bamboohr,
    fetch_company_jobs_lever,
    fetch_company_jobs_workday,
    fetch_company_jobs_icims,
    USER_AGENTS,
)
 
SAMPLE_SIZE = 10

SAMPLES = {
    "Greenhouse": (fetch_company_jobs_greenhouse, ["accenturefederalservices", "canonical"]),

    "Ashby":      (fetch_company_jobs_ashby,      ["confluent", "zip"]),

    "BambooHR":   (fetch_company_jobs_bamboohr,   ["agilebridge", "legato"]),

    "Lever":      (fetch_company_jobs_lever,      ["hermeus", "wyetechllc"]),

    "Workday":    (fetch_company_jobs_workday,    ["kohls|wd1|kohlscareers","2020companies|wd1|external_careers"]),

    "iCIMS":      (fetch_company_jobs_icims,      ["orange", "libertymutual"]),
}
 
# ATSs where the url string is constructed. A PATTERN_BROKEN here points at
# or the others (pass-through), it points at the provider
# API shape changing so extraction returned an empty/missing URL.
CONSTRUCTED_URL_ATS = {"Ashby", "BambooHR", "Workday"}
 
 
def collect_sample_urls(fetch_fn, slugs):
    """Run the real fetch path for each sample company, return up to
    SAMPLE_SIZE job URLs. Empty list means extraction yielded nothing."""
    urls = []
    for slug in slugs:
        try:
            _, jobs, _ = fetch_fn(slug)
        except Exception as e:
            print(f"    fetch failed for {slug}: {e}")
            continue
        for job in jobs:
            url = job.get("url")
            if url:
                urls.append(url)
            if len(urls) >= SAMPLE_SIZE:
                return urls
    return urls
 
 
def url_resolves(url):
    """
    HEAD the URL, following redirects. 2xx/3xx = alive.
    """
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        resp = requests.head(url, allow_redirects=True, timeout=15, headers=headers)
        if resp.status_code == 405:  # some hosts reject HEAD; fall back to GET
            resp = requests.get(url, allow_redirects=True, timeout=15, headers=headers)
        return resp.status_code < 400
    except requests.RequestException:
        return False
 
 
def check_ats(name, fetch_fn, slugs):
    urls = collect_sample_urls(fetch_fn, slugs)
    if not urls:
        # Extraction produced no URLs at all - parse path may have broken,
        # or every sample company is genuinely empty. Either way, flag it.
        return name, 0, 0, "NO_URLS"
 
    alive = 0
    for url in urls:
        if url_resolves(url):
            alive += 1
        time.sleep(random.uniform(0.5, 1.5))  # polite spacing to avoid blocks
 
    total = len(urls)
    if alive == 0:
        status = "PATTERN_BROKEN"
    elif alive < total * 0.5:
        status = "DEGRADED"  # informational - unusually high failure rate
    else:
        status = "OK"
    return name, alive, total, status
 
 
def diagnose(name, status):
    if status == "PATTERN_BROKEN":
        if name in CONSTRUCTED_URL_ATS:
            return "The built URL is likely stale (you construct this URL)"
        return "The provider API shape likely changed (URL is pass-through)"
    if status == "NO_URLS":
        return "Extraction returned nothing - parse path or all samples empty"
    return ""
 
 
def main():
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    summary_lines = []
    failures = []
    for name, (fetch_fn, slugs) in SAMPLES.items():
        name, alive, total, status = check_ats(name, fetch_fn, slugs)
        note = diagnose(name, status)
        line = f"{name:12} {alive}/{total} alive  -> {status}"
        if note:
            line += f"  ({note})"
        print(line)
        summary_lines.append(line)
        if status in ("PATTERN_BROKEN", "NO_URLS"):
            failures.append(name)
 
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("\n".join(summary_lines) + "\n")

    if failures:
        alert = f"\n[ALERT] investigate before the scrape: {', '.join(failures)}"
        print(alert)
        sys.exit(1)

    print("\nAll ATSs healthy.")
 
 
if __name__ == "__main__":
    main()
 