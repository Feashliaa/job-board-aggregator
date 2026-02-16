# Job Board Aggregator

Automated job board aggregating 200,000+ positions from 5,000+ companies across five major ATS platforms. Updated daily via GitHub Actions.

## Live Site

[View Job Board](https://feashliaa.github.io/job-board-aggregator)

## Features

- **Multi-platform scraping**: Greenhouse, Lever, Ashby, BambooHR, and Workday APIs scraped in parallel using `concurrent.futures`
- **Progressive loading**: Chunked gzip data loaded via Web Workers for fast initial render
- **Advanced filtering**: Filter by title, company, location, ATS platform, experience level, and exclude keywords. Toggle remote-only, hide recruiter postings, or hide already-applied jobs
- **Job tier classification**: Automatic skill-level tagging (intern/entry/mid/senior) using weighted keyword scoring on job titles
- **Application tracking**: Mark jobs as saved, applied, or ignored with batch update support via localStorage
- **URL state sync**: Filter/sort/page state persisted in the URL for shareable/bookmarkable searches
- **Responsive design**: Desktop table view with card-based mobile layout
- **Automated pipeline**: Daily GitHub Actions workflow: scrape → merge with existing data → commit chunks → create release

## Tech Stack

| Layer    | Tools                                                  |
| -------- | ------------------------------------------------------ |
| Frontend | Vanilla JavaScript (ES Modules), Bootstrap 5, HTML/CSS |
| Scraping | Python 3.12, `requests`, `concurrent.futures`, `gzip`  |
| Data     | Chunked gzip JSON, Web Workers for decompression       |
| CI/CD    | GitHub Actions (daily cron + manual dispatch)          |
| Hosting  | GitHub Pages                                           |

## Architecture

```
scripts/
├── scraper.py          # Multi-ATS scraper with parallel fetching
└── merge_data.py       # Deduplicates and prunes stale jobs (>30 days)

js/
├── app.js              # Main app class and initialization
├── jobs_loader.js      # Progressive chunk loading + Web Worker orchestration
├── chunk_worker.js     # Web Worker for gzip decompression
├── filters.js          # Filter logic with regex matching
├── sorting.js          # Client-side sort with alpha/numeric handling
├── renderer.js         # Table/card rendering with pagination
├── storage.js          # localStorage wrapper for application tracking
├── columns.js          # Column definitions and custom renderers
├── events.js           # Event listener setup
├── url_state.js        # URL query string sync
└── ui_utils.js         # Toast notifications, HTML escaping, utilities

data/
├── jobs_manifest.json  # Chunk index with metadata
├── jobs_chunk_*.json.gz# Gzipped job data (~25k jobs per chunk)
└── *_companies.json    # Company lists per ATS platform
```

## Data Pipeline

1. **Scrape**: `scraper.py` fetches jobs from all five ATS APIs concurrently (30 workers per platform, 10 for BambooHR to respect rate limits)
2. **Classify**: Each job is tagged with a skill level based on title keywords and flagged if posted by a recruiting agency
3. **Clean**: Jobs missing titles, URLs, or company info are dropped
4. **Chunk**: Results are split into ~25k-job gzipped chunks with a manifest file
5. **Merge**: `merge_data.py` deduplicates against existing data and prunes jobs older than 30 days
6. **Deploy**: GitHub Actions commits updated chunks and creates a tagged release

## Local Development

```bash
git clone https://github.com/Feashliaa/job-board-aggregator.git
cd job-board-aggregator
python -m http.server 8000
# Visit http://localhost:8000
```

To run the scraper locally:

```bash
cd scripts
pip install -r requirements.txt
python scraper.py --source manual
```

## License

This project is licensed under the MIT License ==> see the [LICENSE](LICENSE) file for details.

---

Built by [Riley Dorrington](https://github.com/Feashliaa)