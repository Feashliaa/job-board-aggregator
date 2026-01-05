// ============================================================
// JOB BOARD APP 
// ============================================================

class JobBoardApp {
    constructor() {
        this.allJobs = [];
        this.filteredJobs = [];
        this.currentPage = 1;
        this.perPage = 50;
        this.sortState = { key: null, direction: 'asc' };
        this.filterState = { title: '', company: '', location: '' };

        // Column configuration
        this.columns = [
            { key: 'company', label: 'Company', sortable: true },
            { key: 'title', label: 'Title', sortable: true },
            { key: 'location', label: 'Location', sortable: true },
            {
                key: 'url',
                label: 'Job URL',
                sortable: false,
                render: job => {
                    const url = job.absolute_url || job.url;
                    return url
                        ? `<a href="${this.escape(url)}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary" title="Open job">Link</a>`
                        : 'N/A';
                }
            }
        ];
    }

    // Safe HTML escaping
    escape(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str.toString();
        return div.innerHTML;
    }

    async init() {
        await this.loadJobs();
        this.setupEventListeners();
    }

    // ============================================================
    // LOAD JOBS
    // ============================================================
    async loadJobs() {
        const loadingEl = document.getElementById('loading');
        const resultsEl = document.getElementById('results');

        try {
            // Fetch compressed JSON from repo
            const response = await fetch('./data/all_jobs.json.gz');

            if (!response.ok) throw new Error('Failed to load jobs');

            // Decompress gzip
            const blob = await response.blob();
            const ds = new DecompressionStream('gzip');
            const decompressedStream = blob.stream().pipeThrough(ds);
            const decompressedBlob = await new Response(decompressedStream).blob();
            const text = await decompressedBlob.text();
            const data = JSON.parse(text);

            this.allJobs = data;
            this.filteredJobs = data;

            // Update stats
            const companies = new Set(data.map(j => j.company_slug || j.company)).size;
            document.getElementById('total-jobs').textContent = data.length.toLocaleString();
            document.getElementById('total-companies').textContent = companies.toLocaleString();
            document.getElementById('last-updated').textContent = new Date().toLocaleDateString();

            // Show results
            loadingEl.style.display = 'none';
            resultsEl.style.display = 'block';

            this.render();

        } catch (error) {
            console.error('Error loading jobs:', error);
            loadingEl.innerHTML = `
            <div class="alert alert-danger">
                Failed to load jobs. Please try again later.
                <br><small>${error.message}</small>
            </div>
        `;
        }
    }

    // ============================================================
    // EVENT LISTENERS
    // ============================================================
    setupEventListeners() {
        // Pagination - top
        document.getElementById('prev-page').addEventListener('click', () => this.previousPage());
        document.getElementById('next-page').addEventListener('click', () => this.nextPage());

        // Pagination - bottom
        document.getElementById('prev-page-bottom').addEventListener('click', () => this.previousPage());
        document.getElementById('next-page-bottom').addEventListener('click', () => this.nextPage());

        // Per page selector
        document.getElementById('per-page').addEventListener('change', (e) => {
            this.perPage = parseInt(e.target.value);
            this.currentPage = 1;
            this.render();
        });

        // Filters
        document.getElementById('apply-filters').addEventListener('click', () => this.applyFilters());
        document.getElementById('clear-filters').addEventListener('click', () => this.clearFilters());

        // Enter key on filter inputs
        ['filter-title', 'filter-company', 'filter-location'].forEach(id => {
            document.getElementById(id).addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.applyFilters();
            });
        });

        // Sorting - attach to table headers
        document.querySelectorAll('.job-table thead th').forEach((th, index) => {
            const column = this.columns[index];
            if (column && column.sortable) {
                th.style.cursor = 'pointer';
                th.addEventListener('click', () => this.handleSort(column.key));
            }
        });
    }

    // ============================================================
    // PAGINATION
    // ============================================================
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.render();
            window.scrollTo(0, 0);
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.filteredJobs.length / this.perPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.render();
            window.scrollTo(0, 0);
        }
    }

    updatePagination(totalPages) {
        const pageInfo = `Page ${this.currentPage} of ${totalPages} (${this.filteredJobs.length.toLocaleString()} jobs)`;

        document.getElementById('page-info').textContent = pageInfo;
        document.getElementById('page-info-bottom').textContent = pageInfo;

        // Enable/disable buttons
        const prevBtns = [document.getElementById('prev-page'), document.getElementById('prev-page-bottom')];
        const nextBtns = [document.getElementById('next-page'), document.getElementById('next-page-bottom')];

        prevBtns.forEach(btn => btn.disabled = this.currentPage === 1);
        nextBtns.forEach(btn => btn.disabled = this.currentPage === totalPages);
    }

    // ============================================================
    // FILTERING
    // ============================================================
    applyFilters() {
        const titleFilter = document.getElementById('filter-title').value.toLowerCase().trim();
        const companyFilter = document.getElementById('filter-company').value.toLowerCase().trim();
        const locationFilter = document.getElementById('filter-location').value.toLowerCase().trim();

        this.filterState = {
            title: titleFilter,
            company: companyFilter,
            location: locationFilter
        };

        this.filteredJobs = this.allJobs.filter(job => {
            const title = (job.title || '').toLowerCase();
            const company = ((job.company || job.company_slug) || '').toLowerCase();
            const location = typeof job.location === 'object'
                ? (job.location.name || '').toLowerCase()
                : (job.location || '').toLowerCase();

            return (
                (!titleFilter || title.includes(titleFilter)) &&
                (!companyFilter || company.includes(companyFilter)) &&
                (!locationFilter || location.includes(locationFilter))
            );
        });

        this.currentPage = 1;
        this.render();
    }

    clearFilters() {
        document.getElementById('filter-title').value = '';
        document.getElementById('filter-company').value = '';
        document.getElementById('filter-location').value = '';

        this.filterState = { title: '', company: '', location: '' };
        this.filteredJobs = [...this.allJobs];
        this.currentPage = 1;
        this.render();
    }

    // ============================================================
    // SORTING
    // ============================================================
    handleSort(key) {
        if (this.sortState.key === key) {
            // Toggle direction
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // New sort key
            this.sortState.key = key;
            this.sortState.direction = 'asc';
        }

        this.render();
    }

    applySorting(jobs) {
        if (!this.sortState.key) return jobs;

        const { key, direction } = this.sortState;
        const asc = direction === 'asc';

        return [...jobs].sort((a, b) => {
            let aVal = a[key] || '';
            let bVal = b[key] || '';

            // Handle location object
            if (key === 'location') {
                aVal = typeof aVal === 'object' ? (aVal.name || '') : aVal;
                bVal = typeof bVal === 'object' ? (bVal.name || '') : bVal;
            }

            // Handle company_slug fallback
            if (key === 'company') {
                aVal = aVal || a.company_slug || '';
                bVal = bVal || b.company_slug || '';
            }

            // String comparison
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();

            if (aVal < bVal) return asc ? -1 : 1;
            if (aVal > bVal) return asc ? 1 : -1;
            return 0;
        });
    }

    updateSortIndicators() {
        document.querySelectorAll('.job-table thead th').forEach((th, index) => {
            th.classList.remove('sorted-asc', 'sorted-desc');
            const column = this.columns[index];

            if (column && column.key === this.sortState.key) {
                th.classList.add(
                    this.sortState.direction === 'asc' ? 'sorted-asc' : 'sorted-desc'
                );
            }
        });
    }

    // ============================================================
    // RENDERING
    // ============================================================
    render() {
        const tbody = document.getElementById('jobs-body');

        // Apply sorting to filtered jobs
        const sortedJobs = this.applySorting(this.filteredJobs);

        const totalPages = Math.ceil(sortedJobs.length / this.perPage);

        // Bounds check
        if (this.currentPage > totalPages && totalPages > 0) this.currentPage = 1;
        if (this.currentPage < 1) this.currentPage = 1;

        const start = (this.currentPage - 1) * this.perPage;
        const end = start + this.perPage;
        const pageJobs = sortedJobs.slice(start, end);

        // Clear table
        tbody.innerHTML = '';

        if (pageJobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No jobs found</td></tr>';
            this.updatePagination(1);
            this.updateSortIndicators();
            return;
        }

        // Render rows
        pageJobs.forEach(job => {
            const row = tbody.insertRow();

            this.columns.forEach(col => {
                const cell = row.insertCell();
                cell.setAttribute('data-label', col.label);

                if (col.render) {
                    cell.innerHTML = col.render(job);
                } else {
                    let value = job[col.key];

                    // Handle location object
                    if (col.key === 'location' && typeof value === 'object') {
                        value = value.name || 'Not specified';
                    }

                    // Handle company fallback
                    if (col.key === 'company') {
                        value = value || job.company_slug || 'Unknown';
                    }

                    cell.textContent = value || 'Not specified';
                }
            });
        });

        this.updatePagination(totalPages);
        this.updateSortIndicators();
    }
}

// ============================================================
// INITIALIZE APP
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const app = new JobBoardApp();
    app.init();
});