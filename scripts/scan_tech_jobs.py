import json
import re

# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "output/tech_jobs.json"
OUTPUT_FILE = "output/remote_junior_jobs.json"

# ============================================================
# FILTER CRITERIA
# ============================================================

# Remote location keywords
REMOTE_KEYWORDS = [
    'remote',
    'work from home',
    'wfh',
    'anywhere',
    'distributed',
    'virtual',
    'telecommute',
]

# Junior/Entry level keywords in title
JUNIOR_KEYWORDS = [
    'entry',
    'junior',
    'jr',
    'jr.',
    'associate',
    'graduate',
    'new grad',
    'early career',
    'i',  # Software Engineer I
    '1',  # Software Engineer 1
    'intern',
    'apprentice',
    'trainee',
]

# Keywords that indicate NOT junior (exclude these)
SENIOR_KEYWORDS = [
    'senior',
    'sr',
    'sr.',
    'lead',
    'principal',
    'staff',
    'architect',
    'manager',
    'director',
    'head of',
    'vp',
    'vice president',
    'chief',
    'expert',
    'iii',  # Software Engineer III
    'iv',   # Software Engineer IV
    '3',    # Software Engineer 3
    '4',    # Software Engineer 4
    '5',    # Software Engineer 5
]

# ============================================================
# FILTER FUNCTIONS
# ============================================================

def is_remote(location):
    """Check if location indicates remote work."""
    if not location:
        return False
    
    location_lower = location.lower()
    return any(keyword in location_lower for keyword in REMOTE_KEYWORDS)

def is_junior(title):
    """Check if title indicates junior/entry level position."""
    if not title:
        return False
    
    title_lower = title.lower()
    
    # First, exclude senior positions
    if any(keyword in title_lower for keyword in SENIOR_KEYWORDS):
        return False
    
    # Check for junior indicators
    # Special handling for numbered positions (e.g., "Software Engineer I" or "Engineer 1")
    if re.search(r'\b(i|1)\b', title_lower):
        return True
    
    # Check other junior keywords
    return any(keyword in title_lower for keyword in JUNIOR_KEYWORDS)

def filter_jobs(jobs):
    """Filter jobs for remote + junior positions."""
    filtered = []
    
    for job in jobs:
        title = job.get('title', '')
        location = job.get('location', '')
        
        if is_remote(location) and is_junior(title):
            filtered.append(job)
    
    return filtered

# ============================================================
# MAIN
# ============================================================

def main():
    print("="*80)
    print("FILTERING FOR REMOTE JUNIOR TECH JOBS")
    print("="*80 + "\n")
    
    # Load jobs
    print(f"Loading jobs from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r') as f:
            all_jobs = json.load(f)
        print(f"Loaded {len(all_jobs):,} tech jobs\n")
    except FileNotFoundError:
        print(f"File not found: {INPUT_FILE}")
        print("Make sure you've run the tech job aggregator first!\n")
        return
    
    # Filter
    print("Filtering for remote + junior positions...")
    remote_junior_jobs = filter_jobs(all_jobs)
    
    print(f"Found {len(remote_junior_jobs):,} remote junior jobs\n")
    
    # Show some examples
    if remote_junior_jobs:
        print("Sample jobs found:")
        print("-" * 80)
        for job in remote_junior_jobs[:10]:
            print(f"{job['title']:<50} | {job['location']:<20} | {job['company']}")
        
        if len(remote_junior_jobs) > 10:
            print(f"... and {len(remote_junior_jobs) - 10} more")
        print()
    
    # Save results
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(remote_junior_jobs, f, indent=2)
    
    print(f"Saved {len(remote_junior_jobs):,} jobs\n")
    
    # Statistics
    print("="*80)
    print("STATISTICS")
    print("="*80)
    print(f"Total tech jobs:        {len(all_jobs):,}")
    print(f"Remote junior jobs:     {len(remote_junior_jobs):,}")
    print(f"Percentage:             {len(remote_junior_jobs)/len(all_jobs)*100:.2f}%")
    print("\nDone!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()