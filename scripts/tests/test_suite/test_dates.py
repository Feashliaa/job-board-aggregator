"""
Tests for the date-sorting feature:
  1. updated_at field — verifies each ATS scraper extracts a date where expected.
  2. first_seen logic  — unit tests the merge-loop logic with synthetic data (no I/O).
  3. _parse_workday_posted_on — unit tests the Workday relative-date parser.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper import (
    fetch_company_jobs_greenhouse,
    fetch_company_jobs_ashby,
    fetch_company_jobs_icims,
    fetch_company_jobs_workday,
    _parse_workday_posted_on,
)
from merge_data import get_dedup_key

# ── Configuration ─────────────────────────────────────────────────────────────

FETCH_LIMIT = 20   # max jobs to inspect per ATS

# (fetch_fn, sample_slugs, must_have_dates)
# must_have_dates=True  → FAIL if 0 jobs have updated_at
# must_have_dates=False → WARN only (field is best-effort for this ATS)
ATS_SAMPLES = {
    "Greenhouse": (fetch_company_jobs_greenhouse, ["accenturefederalservices", "canonical"],                    True),
    "Ashby":      (fetch_company_jobs_ashby,      ["confluent", "zip"],                                        False),
    "iCIMS":      (fetch_company_jobs_icims,      ["orange", "libertymutual"],                                 False),
    "Workday":    (fetch_company_jobs_workday,    ["kohls|wd1|kohlscareers", "2020companies|wd1|external_careers"], False),
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def collect_jobs(fetch_fn, slugs, limit):
    jobs = []
    for slug in slugs:
        try:
            _, batch, _ = fetch_fn(slug)
        except Exception as e:
            print(f"    fetch failed for {slug}: {e}")
            continue
        jobs.extend(batch)
        if len(jobs) >= limit:
            break
    return jobs[:limit]


def check_updated_at(name, fetch_fn, slugs, must_have_dates):
    """Fetch sample jobs and report updated_at coverage."""
    jobs = collect_jobs(fetch_fn, slugs, FETCH_LIMIT)
    if not jobs:
        return name, 0, 0, "NO_JOBS"

    with_date = [j for j in jobs if j.get("updated_at")]
    total = len(jobs)
    count = len(with_date)

    # Validate format for any dates we did get
    bad_format = []
    for j in with_date:
        raw = j["updated_at"]
        try:
            datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            bad_format.append(raw)

    if bad_format:
        return name, count, total, f"BAD_FORMAT ({bad_format[0]!r})"

    if count == 0 and must_have_dates:
        return name, count, total, "MISSING"

    if count == 0:
        return name, count, total, "NONE (expected — field is best-effort)"

    return name, count, total, "OK"


# ── Unit tests: first_seen merge logic ────────────────────────────────────────

def _run_merge_logic(existing_jobs, new_jobs):
    """Replicate the merge loop from merge_data.py for unit testing."""
    merged = {get_dedup_key(j): j for j in existing_jobs if get_dedup_key(j)}

    for job in new_jobs:
        key = get_dedup_key(job)
        if key:
            existing = merged.get(key)
            if existing:
                job["first_seen"] = existing.get("first_seen") or existing.get("scraped_at")
            else:
                job["first_seen"] = job.get("scraped_at")
            merged[key] = job

    return merged


def _job(url, scraped_at=None, first_seen=None, ats="Greenhouse"):
    j = {"url": url, "ats": ats, "title": "Eng", "company": "acme"}
    if scraped_at:
        j["scraped_at"] = scraped_at
    if first_seen:
        j["first_seen"] = first_seen
    return j


def test_first_seen_new_job():
    """A brand-new job gets first_seen = its own scraped_at."""
    new = [_job("https://example.com/1", scraped_at="2025-01-10T00:00:00Z")]
    result = _run_merge_logic(existing_jobs=[], new_jobs=new)
    job = result["https://example.com/1"]
    assert job["first_seen"] == "2025-01-10T00:00:00Z", (
        f"expected 2025-01-10T00:00:00Z, got {job['first_seen']!r}"
    )


def test_first_seen_preserved_on_rescrape():
    """Re-scraping a known job must NOT overwrite first_seen."""
    existing = [_job("https://example.com/2",
                     scraped_at="2025-01-01T00:00:00Z",
                     first_seen="2025-01-01T00:00:00Z")]
    new      = [_job("https://example.com/2", scraped_at="2025-02-01T00:00:00Z")]
    result = _run_merge_logic(existing, new)
    job = result["https://example.com/2"]
    assert job["first_seen"] == "2025-01-01T00:00:00Z", (
        f"first_seen should not change on rescrape, got {job['first_seen']!r}"
    )


def test_first_seen_seeded_from_scraped_at_when_missing():
    """Existing job that pre-dates this feature (no first_seen) gets seeded
    from scraped_at on the next merge run."""
    existing = [_job("https://example.com/3", scraped_at="2024-12-01T00:00:00Z")]
    new      = [_job("https://example.com/3", scraped_at="2025-01-15T00:00:00Z")]
    result = _run_merge_logic(existing, new)
    job = result["https://example.com/3"]
    assert job["first_seen"] == "2024-12-01T00:00:00Z", (
        f"first_seen should be seeded from old scraped_at, got {job['first_seen']!r}"
    )


def test_first_seen_independent_jobs():
    """Two different URLs each get their own first_seen independently."""
    new = [
        _job("https://example.com/a", scraped_at="2025-03-01T00:00:00Z"),
        _job("https://example.com/b", scraped_at="2025-03-02T00:00:00Z"),
    ]
    result = _run_merge_logic(existing_jobs=[], new_jobs=new)
    assert result["https://example.com/a"]["first_seen"] == "2025-03-01T00:00:00Z"
    assert result["https://example.com/b"]["first_seen"] == "2025-03-02T00:00:00Z"


def test_first_seen_no_scraped_at():
    """Job with no scraped_at gets first_seen=None rather than crashing."""
    new = [_job("https://example.com/noscrape")]
    result = _run_merge_logic(existing_jobs=[], new_jobs=new)
    job = result["https://example.com/noscrape"]
    assert "first_seen" in job, "first_seen key should always be set"
    assert job["first_seen"] is None


# ── Unit tests: Workday posted-on parser ──────────────────────────────────────

def test_workday_parse_today():
    result = _parse_workday_posted_on("Posted Today")
    assert result == date.today().isoformat(), f"got {result!r}"


def test_workday_parse_days():
    result = _parse_workday_posted_on("Posted 2 Days Ago")
    expected = (date.today() - timedelta(days=2)).isoformat()
    assert result == expected, f"got {result!r}"


def test_workday_parse_weeks():
    result = _parse_workday_posted_on("Posted 1 Week Ago")
    expected = (date.today() - timedelta(weeks=1)).isoformat()
    assert result == expected, f"got {result!r}"


def test_workday_parse_months():
    result = _parse_workday_posted_on("Posted 2 Months Ago")
    expected = (date.today() - timedelta(days=60)).isoformat()
    assert result == expected, f"got {result!r}"


def test_workday_parse_none():
    assert _parse_workday_posted_on(None) is None
    assert _parse_workday_posted_on("") is None
    assert _parse_workday_posted_on("some unknown string") is None


def test_workday_parse_returns_iso():
    """Result must be a valid ISO date string parseable by datetime."""
    result = _parse_workday_posted_on("Posted 5 Days Ago")
    assert result is not None
    datetime.fromisoformat(result)   # raises if not valid ISO


def run_unit_tests():
    tests = [
        test_first_seen_new_job,
        test_first_seen_preserved_on_rescrape,
        test_first_seen_seeded_from_scraped_at_when_missing,
        test_first_seen_independent_jobs,
        test_first_seen_no_scraped_at,
        test_workday_parse_today,
        test_workday_parse_days,
        test_workday_parse_weeks,
        test_workday_parse_months,
        test_workday_parse_none,
        test_workday_parse_returns_iso,
    ]
    passed, failed = 0, []
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed.append(t.__name__)
    return passed, failed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    summary_lines = []
    failures = []

    # 1. Unit tests (no network)
    print("── first_seen merge logic (unit tests) ──")
    passed, unit_failures = run_unit_tests()
    unit_line = f"first_seen unit tests: {passed} passed, {len(unit_failures)} failed"
    print(unit_line)
    summary_lines.append(unit_line)
    failures.extend(unit_failures)
    print()

    # 2. Network tests — updated_at field coverage per ATS
    print("── updated_at field coverage (network) ──")
    for name, (fetch_fn, slugs, must_have_dates) in ATS_SAMPLES.items():
        name, count, total, status = check_updated_at(name, fetch_fn, slugs, must_have_dates)
        coverage = f"{count}/{total}" if total else "0/0"
        line = f"{name:12} updated_at: {coverage:6}  -> {status}"
        print(line)
        summary_lines.append(line)
        if status in ("MISSING", "BAD_FORMAT", "NO_JOBS") and must_have_dates:
            failures.append(name)

    if summary_path:
        with open(summary_path, "a") as f:
            f.write("\n## Date Field Tests\n")
            f.write("\n".join(summary_lines) + "\n")

    if failures:
        alert = f"\n[ALERT] date field failures: {', '.join(failures)}"
        print(alert)
        sys.exit(1)

    print("\nAll date field checks passed.")


if __name__ == "__main__":
    main()
