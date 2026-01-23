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
        this.filterState = { title: '', company: '', location: '', status: '' };
        this.debounceTimer = null;

        // Column configuration
        this.columns = [
            {
                key: 'status',
                label: 'Status',
                sortable: false,
                render: job => {
                    const url = job.absolute_url || job.url;
                    const apps = this.loadApplicationStatus();
                    const current = apps[url]?.status || '';

                    const options = [
                        { value: '', label: '-', color: 'secondary' },
                        { value: 'saved', label: 'Saved', color: 'info' },
                        { value: 'applied', label: 'Applied', color: 'success' },
                        { value: 'ignored', label: 'Ignored', color: 'dark' }
                    ];

                    const selectedOption = options.find(opt => opt.value === current) || options[0];

                    return `
                <select class="form-select form-select-sm status-dropdown" 
                        data-job-url="${this.escape(url)}"
                        style="min-width: 100px;">
                    ${options.map(opt => `
                        <option value="${opt.value}" ${opt.value === current ? 'selected' : ''}>
                            ${opt.label}
                        </option>
                    `).join('')}
                </select>
            `;
                }
            },
            { key: 'company', label: 'Company', sortable: true },
            { key: 'title', label: 'Title', sortable: true },
            { key: 'location', label: 'Location', sortable: true },
            {
                key: 'ats',
                label: 'ATS',
                sortable: true,
                render: job => {
                    const ats = job.ats || 'unknown';
                    const colors = {
                        'greenhouse': 'success',
                        'lever': 'primary',
                        'workday': 'warning',
                        'ashby': 'info',
                        'icms': 'secondary',
                        'bamboohr': 'danger',
                        'workable': 'dark',
                        'unknown': 'primary'
                    }
                    const color = colors[ats.toLowerCase()] || 'light';
                    return `<span class="badge bg-${color}">${this.escape(ats)}</span>`;
                }
            },
            {
                key: 'url',
                label: 'Apply',
                sortable: false,
                render: job => {
                    const url = job.absolute_url || job.url;
                    return url
                        ? `<a href="${this.escape(url)}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">Apply</a>`
                        : 'N/A';
                }
            },
            {
                key: 'actions',
                label: 'Actions',
                sortable: false,
                render: job => {
                    const url = job.absolute_url || job.url;
                    return `
                <div class="btn-group" role="group">
                    <input type="checkbox" class="btn-check apply-checkbox" 
                           id="apply-${this.escape(url)}" 
                           data-job-url="${this.escape(url)}">
                    <label class="btn btn-sm btn-outline-success" for="apply-${this.escape(url)}">Applied</label>
                    
                    <input type="checkbox" class="btn-check ignored-checkbox" 
                           id="ignore-${this.escape(url)}" 
                           data-job-url="${this.escape(url)}">
                    <label class="btn btn-sm btn-outline-secondary" for="ignore-${this.escape(url)}">Ignored</label>
                </div>
            `;
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

    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    async init() {
        await this.loadJobs();
        this.setupEventListeners();
        this.loadFromURL();
    }

    // ============================================================
    // LOAD JOBS
    // ============================================================
    async loadJobs() {
        const loadingEl = document.getElementById('loading');
        const resultsEl = document.getElementById('results');

        try {
            // Fetch compressed JSON from repo
            // local testing: scripts/output/all_jobs.json.gz
            // production: ./data/all_jobs.json.gz
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
    // BATCH PROCESSING HANDLER
    // ============================================================
    handleBatch() {
        const selected = document.querySelectorAll('.apply-checkbox:checked, .ignored-checkbox:checked');

        if (selected.length === 0) {
            this.showToast('Please select at least one job first.', 'warning');
            return;
        }

        this.setUIBusy(true);

        try {
            // Process "applied" checkboxes
            const appliedBoxes = document.querySelectorAll('.apply-checkbox:checked');
            appliedBoxes.forEach(box => {
                const jobUrl = box.dataset.jobUrl;
                if (jobUrl) {
                    this.saveApplicationStatus(jobUrl, 'applied');
                }
            });

            // Process "ignored" checkboxes
            const ignoredBoxes = document.querySelectorAll('.ignored-checkbox:checked');
            ignoredBoxes.forEach(box => {
                const jobUrl = box.dataset.jobUrl;
                if (jobUrl) {
                    this.saveApplicationStatus(jobUrl, 'ignored');
                }
            });

            this.showToast(`Updated ${selected.length} job(s) successfully!`, 'success');

            // Hide FAB after processing
            this.updateFABVisibility();

        } catch (err) {
            this.showToast('Error updating job status.', 'danger');
            console.error(err);
        } finally {
            this.setUIBusy(false);
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

        // Status filter
        document.getElementById('filter-status').addEventListener('change', (e) => {
            this.filterState.status = e.target.value;
            this.currentPage = 1;
            this.applyFilters();
        });

        // Hide applied/ignored filter
        document.getElementById('filter-hide-applied').addEventListener('change', () => {
            this.applyFilters();
        });

        // Batch processing buttons
        document.getElementById('process-batch').addEventListener('click', () => this.handleBatch());
        document.getElementById('process-fab').addEventListener('click', () => this.handleBatch());

        // Status dropdown changes (delegated)
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('status-dropdown')) {
                const url = e.target.dataset.jobUrl;
                const status = e.target.value;
                if (status) {
                    this.saveApplicationStatus(url, status);
                    this.showToast(`Job marked as ${status}`, 'success');
                } else {
                    this.deleteApplicationStatus(url);
                    this.showToast('Status cleared', 'info');
                }
            }
        });

        // Show/hide FAB based on selections
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('apply-checkbox') || e.target.classList.contains('ignored-checkbox')) {
                this.updateFABVisibility();
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
        const hideRecruiters = document.getElementById('filter-hide-recruiters').checked;
        const remoteOnly = document.getElementById('filter-remote-only').checked;
        const hideApplied = document.getElementById('filter-hide-applied').checked;
        const titleFilter = document.getElementById('filter-title').value.toLowerCase().trim();
        const companyFilter = document.getElementById('filter-company').value.toLowerCase().trim();
        const locationFilter = document.getElementById('filter-location').value.toLowerCase().trim();
        const statusFilter = document.getElementById('filter-status').value;

        const apps = this.loadApplicationStatus();

        const titleRegex = titleFilter ? new RegExp(`\\b${this.escapeRegex(titleFilter)}\\b`, 'i') : null;
        const companyRegex = companyFilter ? new RegExp(`\\b${this.escapeRegex(companyFilter)}\\b`, 'i') : null;
        const locationRegex = locationFilter ? new RegExp(`\\b${this.escapeRegex(locationFilter)}\\b`, 'i') : null;

        this.filterState = {
            title: titleFilter,
            company: companyFilter,
            location: locationFilter,
            remoteOnly: remoteOnly,
            status: statusFilter
        };

        this.filteredJobs = this.allJobs.filter(job => {

            if (hideRecruiters && job.is_recruiter === true) {
                return false;
            }

            const url = job.absolute_url || job.url;
            const jobStatus = apps[url]?.status || ''; // Load application status

            if (hideApplied && (jobStatus === 'applied' || jobStatus === 'ignored')) {
                return false;
            }

            if (statusFilter && jobStatus !== statusFilter) {
                return false;
            }

            const title = (job.title || '').toLowerCase();
            const company = ((job.company || job.company_slug) || '').toLowerCase();
            let location = '';
            if (job.location) {
                location = typeof job.location === 'object'
                    ? (job.location.name || '').toLowerCase()
                    : (job.location || '').toLowerCase();
            }

            // remote only filter
            if (remoteOnly) {
                const isRemote = location.includes('remote')
                    || (job.workplaceType && job.workplaceType.toLowerCase() === 'remote')
                if (!isRemote) {
                    return false;
                }
            }

            return (
                (!titleRegex || titleRegex.test(title)) &&
                (!companyRegex || companyRegex.test(company)) &&
                (!locationRegex || locationRegex.test(location))
            );
        });

        this.currentPage = 1;
        this.updateURL();
        this.render();
    }

    clearFilters() {
        document.getElementById('filter-title').value = '';
        document.getElementById('filter-company').value = '';
        document.getElementById('filter-location').value = '';
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-hide-recruiters').checked = true;
        document.getElementById('filter-remote-only').checked = false;
        document.getElementById('filter-hide-applied').checked = false;

        this.filterState = { title: '', company: '', location: '', remoteOnly: false, status: '' };
        this.filteredJobs = [...this.allJobs];
        this.currentPage = 1;
        this.updateURL();
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
                if (aVal && typeof aVal === 'object') {
                    aVal = aVal.name || '';
                }
                if (bVal && typeof bVal === 'object') {
                    bVal = bVal.name || '';
                }
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
                    if (col.key === 'location') {
                        if (value && typeof value === 'object') {
                            value = value.name || 'Not specified';
                        } else {
                            value = value || 'Not specified';
                        }
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

    // ============================================================
    // URL STATE MANAGEMENT
    // ============================================================
    updateURL() {
        const params = new URLSearchParams();
        if (this.filterState.title) params.set('title', this.filterState.title);
        if (this.filterState.company) params.set('company', this.filterState.company);
        if (this.filterState.location) params.set('location', this.filterState.location);
        if (this.filterState.remoteOnly) params.set('remote', '1');
        if (this.currentPage > 1) params.set('page', this.currentPage.toString());

        const newURL = params.toString()
            ? `${window.location.pathname}?${params.toString()}`
            : window.location.pathname;

        window.history.replaceState({}, '', newURL);
    }

    loadFromURL() {
        const params = new URLSearchParams(window.location.search);

        const title = params.get('title') || '';
        const company = params.get('company') || '';
        const location = params.get('location') || '';
        const remote = params.get('remote') === '1';
        const page = parseInt(params.get('page')) || 1;

        document.getElementById('filter-title').value = title;
        document.getElementById('filter-company').value = company;
        document.getElementById('filter-location').value = location;
        document.getElementById('filter-remote-only').checked = remote;

        this.currentPage = page;

        if (title || company || location || remote) {
            this.applyFilters();
        }
    }

    // ============================================================
    // DEBOUNCE RENDERING
    // ============================================================

    debounceRender() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.render(), 300);
    }

    setUIBusy(isBusy) {
        const controls = ['#apply-filters', '#clear-filters', '#prev-page', '#next-page'];
        controls.forEach(sel => {
            const el = document.querySelector(sel);
            if (el) el.disabled = isBusy;
        });
        document.body.style.cursor = isBusy ? 'wait' : 'default';
    }

    // ============================================================
    // Toast Notifications
    // ============================================================
    showLoadingToast(message = 'Loading, please wait...') {
        const toastEl = document.getElementById('job-toast');
        const body = document.getElementById('toast-message');
        if (!toastEl) return { hide: () => { } };

        // hard cancel any running transition
        toastEl.classList.remove('show');
        toastEl.offsetHeight;

        // force cleanup of any instance
        const existingInstance = bootstrap.Toast.getInstance(toastEl);
        if (existingInstance) {
            try { existingInstance.dispose(); } catch { }
        }

        // Style for loading spinner toast
        toastEl.className = 'toast align-items-center text-white bg-secondary border-0';
        body.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <div class="spinner-border spinner-border-sm text-light" role="status"></div>
            <span>${message}</span>
        </div>`;

        // Show the toast
        const toastInstance = bootstrap.Toast.getOrCreateInstance(toastEl, { autohide: false });
        toastInstance.show();

        // Return controller for hiding it later
        return {
            hide: () => {
                const instance = bootstrap.Toast.getInstance(toastEl);
                if (instance && toastEl.classList.contains('show')) instance.hide();
            }
        };
    }

    showToast(message, type = 'primary') {
        const toastEl = document.getElementById('job-toast');
        const body = document.getElementById('toast-message');
        if (!toastEl) return { hide: () => { } };

        // hard cancel any running transition
        toastEl.classList.remove('show');
        toastEl.offsetHeight;

        // force cleanup of any instance
        const existingInstance = bootstrap.Toast.getInstance(toastEl);
        if (existingInstance) {
            try { existingInstance.dispose(); } catch { }
        }

        // Reset class and set color
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        body.textContent = message;

        // Display toast with short delay
        const toastInstance = bootstrap.Toast.getOrCreateInstance(toastEl, { autohide: true, delay: 4000 });
        toastInstance.show();

        return {
            hide: () => {
                const instance = bootstrap.Toast.getInstance(toastEl);
                if (instance && toastEl.classList.contains('show')) instance.hide();
            }
        };
    }

    // ============================================================
    // Local STORAGE UTILITIES
    // ============================================================
    loadApplicationStatus() {
        const saved = localStorage.getItem('job-applications');
        return saved ? JSON.parse(saved) : {};
    }

    saveApplicationStatus(jobUrl, status) {
        const apps = this.loadApplicationStatus();
        apps[jobUrl] = {
            status: status, // 'saved', 'applied', 'ignored'
            date: new Date().toISOString()
        };
        localStorage.setItem('job-applications', JSON.stringify(apps));
        this.render(); // Re-render to show updated status
    }

    deleteApplicationStatus(jobUrl) {
        const apps = this.loadApplicationStatus();
        delete apps[jobUrl];
        localStorage.setItem('job-applications', JSON.stringify(apps));
        this.render();
    }

    // ============================================================
    // UTILITIES
    // ============================================================

    parseSalary(salaryString) {
        if (!salaryString) return null;

        // Remove $, commas, whitespace
        let s = salaryString.replace(/\$/g, '').replace(/,/g, '').trim().toLowerCase();

        // Detect hourly or yearly
        const isHourly = s.includes('/hr');
        const isYearly = s.includes('/yr') || s.includes('/year');

        // Extract numeric part before /hr or /yr
        let parts = s.split('/')[0];
        let range = parts.split('-').map(x => x.trim());

        const convert = (val) => {
            if (!val) return null;
            if (val.includes('k')) return parseFloat(val) * 1000;
            return parseFloat(val);
        };

        let min = convert(range[0]);
        let max = convert(range[1] ?? range[0]);

        if (min == null || isNaN(min)) return null;

        // Normalize hourly → yearly
        if (isHourly) {
            min *= 2080;
            max *= 2080;
        }

        return { min, max };
    }

    updateFABVisibility() {
        const anyChecked = document.querySelectorAll('.apply-checkbox:checked, .ignored-checkbox:checked').length > 0;
        const fabContainer = document.getElementById('process-fab-container');
        fabContainer.style.display = anyChecked ? 'block' : 'none';
    }
}

// ============================================================
// INITIALIZE APP
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const app = new JobBoardApp();
    app.init();
});