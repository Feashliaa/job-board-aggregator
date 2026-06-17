# Check updated_at coverage in the raw scrape output (before merge)
import json
with open("scripts/output/all_jobs.json") as f:
    jobs = json.load(f)

from collections import Counter
coverage = Counter((j["ats"], bool(j.get("updated_at"))) for j in jobs)
for (ats, has_date), count in sorted(coverage.items()):
    print(f"{ats:12} updated_at={'yes' if has_date else 'no ':3}: {count:,}")
