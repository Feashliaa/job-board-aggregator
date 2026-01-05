# Job Board Aggregator

Automated job board aggregating 50,000+ positions from 4,000+ companies using Greenhouse and other ATS platforms.

## Features
- Daily automated scraping via GitHub Actions
- Real-time filtering by title, company, location
- Sortable columns
- Responsive mobile design
- Pagination for large datasets

## Tech Stack
- **Frontend:** Vanilla JavaScript, Bootstrap 5, HTML/CSS
- **Scraping:** Python (requests, concurrent.futures)
- **Deployment:** GitHub Pages + GitHub Actions
- **Data:** JSON hosted on GitHub Releases

## Live Site
[View Job Board](https://feashliaa.github.io/job-board-aggregator)

## Local Development
cd job-board-aggregator
python -m http.server 8000
## Visit http://localhost:8000


Built by [Riley Dorrington](https://github.com/Feashliaa)