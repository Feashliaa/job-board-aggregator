import re, json, os, sys
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CLEAN_FILE = os.path.join(ROOT_DIR, "data", "paylocity_companies_clean.json")

PAGEDATA_RE = re.compile(r"window\.pageData\s*=\s*(\{.*?\});\s*</script>", re.DOTALL)

def resolve_location(j):
    # LocationName is already formatted ("Austin, TX"), trust it first
    return j.get("LocationName") or "Not specified"

def resolve_dept(j, data):
    # try the direct field, then map an id through the top-level Departments lookup
    d = j.get("HiringDepartment")
    if d:
        return d
    dep_id = j.get("DepartmentId") or j.get("HiringDepartmentId")
    if dep_id is not None:
        for dep in (data.get("Departments") or []):
            if dep.get("Id") == dep_id or dep.get("DepartmentId") == dep_id:
                return dep.get("Name") or dep.get("Title")
    return None

def preview_record(j, data, company, slug):
    """Mirror of the pipeline fetcher output, minus the shared helpers."""
    job_id = j.get("JobId")
    title = j.get("JobTitle")
    location = resolve_location(j)
    detail = (f"https://recruiting.paylocity.com/recruiting/Jobs/Details/{job_id}"
              if job_id else None)
    dept = resolve_dept(j, data)
    desc = j.get("Description") or ""
    return {
        "company": company,
        "company_slug": slug,
        "title": title,
        "location": location,
        "remote_flag_IsRemote": j.get("IsRemote"),
        "indeed_remote_type": j.get("IndeedRemoteType"),
        "url": detail,
        "departments": [dept] if dept else [],
        "id": job_id,
        "updated_at": j.get("PublishedDate"),
        "ats": "Paylocity",
        "description_len": len(desc),
        "description_preview": desc[:160].replace("\n", " "),
    }

def fetch(guid, name, session):
    url = f"https://recruiting.paylocity.com/recruiting/jobs/All/{guid}/"
    r = session.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(f"\n{'='*70}\n{name}  ({guid})\n  status: {r.status_code}")
    if r.status_code != 200:
        print("  -> non-200, skipping")
        return
    m = PAGEDATA_RE.search(r.text)
    if not m:
        print("  -> NO pageData blob (soft block or layout change)")
        return
    try:
        data = json.loads(m.group(1))
    except ValueError:
        print("  -> pageData found but JSON parse failed")
        return

    jobs = data.get("Jobs") or []
    print(f"  jobs found: {len(jobs)}")
    print(f"  Departments lookup size: {len(data.get('Departments') or [])}")
    if not jobs:
        return

    j = jobs[0]
    print("\n  --- FULL FIRST JOB (raw pageData job object) ---")
    print(json.dumps(j, indent=2)[:2500])    # cap so one giant description doesn't flood

    print("\n  --- RESOLVED RECORD (what the pipeline will emit) ---")
    print(json.dumps(preview_record(j, data, name, guid), indent=2))

def main():
    with open(CLEAN_FILE) as f:
        rows = json.load(f)
    sample = [r for r in rows if r.get("jobs", 0) > 0][:10]
    if not sample:
        print("No tenants with jobs > 0 in clean file.")
        sys.exit(1)

    print(f"Testing {len(sample)} tenants (loaded {len(rows)} total)")
    session = requests.Session()
    for r in sample:
        try:
            fetch(r["guid"], r.get("name") or r["guid"], session)
        except Exception as e:
            print(f"  ERROR {r['guid']}: {e}")

if __name__ == "__main__":
    main()