import json
import os
import shutil 
from datetime import datetime, timezone  



# ---------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR =  os.path.join(ROOT_DIR, "scripts", "output")
SITE_DIR = os.path.join(ROOT_DIR, "site")

os.makedirs(SITE_DIR, exist_ok=True)

# ----------------

with open(os.path.join(OUTPUT_DIR, "all_jobs.json"), encoding= "utf-8") as file:
    jobs = json.load(file)


with open(os.path.join(OUTPUT_DIR, "metadata.json"), encoding="utf-8") as file:
    metadata = json.load(file)


slim_jobs = [
    {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "url": job.get("url") or job.get("absolute_url"),
        "ats": job.get("ats"),
        "updated_at": job.get("updated_at"),
        "remote": job.get("remote", False),
    }
    for job in jobs
]

with open(os.path.join(SITE_DIR, "jobs.json"), "w", encoding="utf-8") as file:
    json.dump(slim_jobs, file, ensure_ascii=False, separators=(",", ":"))


slim_jobs = [
    {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "url": job.get("url") or job.get("absolute_url"),
        "ats": job.get("ats"),
        "updated_at": job.get("updated_at"),
        "remote": job.get("remote", False),
    }
    for job in jobs
]

with open(os.path.join(SITE_DIR, "jobs.json"), "w", encoding="utf-8") as file:
    json.dump(slim_jobs, file, ensure_ascii=False, separators=(",", ":"))


with open(os.path.join(SITE_DIR, "metadata.json"), "w", encoding="utf-8") as file:
    json.dump(site_metadata, file, ensure_ascii=False, indent=2)

for filename in ("index.html", "styles.css", "app.js"):
    source = os.path.join(ROOT_DIR, "site_template", filename)
    destination = os.path.join(SITE_DIR, filename)
    shutil.copyfile(source, destination)

size_bytes = sum(
    os.path.getsize(os.path.join(root, name))
    for root, _, files in os.walk(SITE_DIR)
    for name in files
)
print(f"Published site size: {size_bytes / 1024 / 1024:.2f} MB")