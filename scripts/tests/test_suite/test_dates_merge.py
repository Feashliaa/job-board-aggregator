# coverage_check.py
import json
from collections import Counter

with open("scripts/output/all_jobs.json", encoding="utf-8") as f:
    jobs = json.load(f)

cov = Counter((j.get("ats", "UNKNOWN"), bool(j.get("updated_at"))) for j in jobs)
for (ats, has_date), count in sorted(cov.items()):
    print(f"{ats:12} updated_at={'yes' if has_date else 'no':3}: {count:,}")