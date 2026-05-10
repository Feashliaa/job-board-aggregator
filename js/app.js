// ============================================================
// JOB BOARD APP 
// ============================================================

import { showToast, showLoadingToast, setUIBusy, updateFABVisibility } from './ui_utils.js';
import { saveApplicationStatus } from './storage.js';
import { createColumns } from './columns.js';
import { loadJobsProgressive, updateStats } from './jobs_loader.js';
import { filterJobs, clearFilterInputs } from './filters.js';
import { render } from './renderer.js';
import { updateURL, loadFromURL } from './url_state.js';
import { setupEventListeners } from './events.js';
import { applySorting } from './sorting.js';
import { toggleView, updateHeatmapIfVisible } from './map_view.js';

class JobBoardApp {
    constructor() {
        this.allJobs = [];
        this.filteredJobs = [];
        this.currentPage = 1;
        this.perPage = window.innerWidth <= 900 ? 25 : 50;
        this.sortState = { key: null, direction: 'asc' };

        this.filterState = {
            title: '', company: '', location: '', status: '',
            ats: '', skill_level: '', remoteOnly: false
        };

        this.debounceTimer = null;
        this.columns = createColumns();
    }

    // ── Initialization ───────────────────────────────────────────
    async init() {
        await this.loadJobs();
        setupEventListeners(this);
        this.loadFromURL();
        this.setupViewToggle();  // ← add this
        this.render();
    }

    // ── Data Loading ───────────────────────────────────────────
    async loadJobs() {
        const loadingEl = document.getElementById('loading');
        const resultsEl = document.getElementById('results');

        try {
            await loadJobsProgressive(this);

            this.sortState = { key: null, direction: 'asc' };

            loadingEl.style.display = 'none';
            resultsEl.style.display = 'block';

            console.log(`Loaded ${this.allJobs.length} jobs (more loading...)`);

        } catch (error) {
            console.error('Error loading jobs:', error);
            showToast('Error loading job data.', 'danger');
            loadingEl.textContent = 'Failed to load job data.';
        }
    }

    // ── Rendering ────────────────────────────────────────────
    render() {
        render(this);
    }

    debounceRender() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.render(), 300);
    }

    // ── Filtering ────────────────────────────────────────────
    applyFilters() {
        const { filteredJobs, filterState } = filterJobs(this.allJobs);
        this.filteredJobs = filteredJobs;
        this.filterState = filterState;
        this.currentPage = 1;
        updateURL(this.filterState, this.currentPage, this.sortState);
        this.render();
        updateHeatmapIfVisible();  // ← add
    }

    clearFilters() {
        clearFilterInputs();
        this.filterState = {
            title: '', company: '', location: '', status: '',
            ats: '', skill_level: '', remoteOnly: false
        };
        this.filteredJobs = [...this.allJobs];
        this.currentPage = 1;
        updateURL(this.filterState, this.currentPage, this.sortState);
        this.render();
        updateHeatmapIfVisible();  // ← add
    }

    refilter() {
        if (this.hasActiveFilters()) {
            this.applyFilters();  // already updates heatmap via applyFilters()
        } else {
            this.filteredJobs = this.allJobs;
            updateHeatmapIfVisible();  // ← add
        }
    }

    hasActiveFilters() {
        const f = this.filterState;
        return f.title || f.company || f.location || f.status ||
            f.ats || f.skill_level || f.remoteOnly || f.exclude || f.include;
    }

    // ── Sorting ──────────────────────────────────────────────
    handleSort(key) {
        if (this.sortState.key === key) {
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortState.key = key;
            this.sortState.direction = 'asc';
        }
        this.currentPage = 1;
        updateURL(this.filterState, this.currentPage, this.sortState);
        this.sortAndRender();
    }

    sortAndRender() {
        const loader = showLoadingToast('Sorting...');
        setTimeout(() => {
            this.render();
            loader.hide();
        }, 100);
    }

    // ── Pagination ───────────────────────────────────────────
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

    // ── URL State ────────────────────────────────────────────
    loadFromURL() {
        const { hasFilters, page } = loadFromURL();
        this.currentPage = page;
        if (hasFilters) this.applyFilters();
    }

    // ── Batch Processing ─────────────────────────────────────
    handleBatch() {
        const selected = document.querySelectorAll('.save-checkbox:checked, .apply-checkbox:checked, .ignored-checkbox:checked');
        if (selected.length === 0) {
            showToast('Please select at least one job first.', 'warning');
            return;
        }

        setUIBusy(true);

        try {
            document.querySelectorAll('.save-checkbox:checked').forEach(box => {
                if (box.dataset.jobUrl) saveApplicationStatus(box.dataset.jobUrl, 'saved');
            });
            document.querySelectorAll('.apply-checkbox:checked').forEach(box => {
                if (box.dataset.jobUrl) saveApplicationStatus(box.dataset.jobUrl, 'applied');
            });
            document.querySelectorAll('.ignored-checkbox:checked').forEach(box => {
                if (box.dataset.jobUrl) saveApplicationStatus(box.dataset.jobUrl, 'ignored');
            });

            showToast(`Updated ${selected.length} job(s) successfully!`, 'success');
            updateFABVisibility();
            this.render();

        } catch (err) {
            showToast('Error updating job status.', 'danger');
            console.error(err);
        } finally {
            setUIBusy(false);
        }
    }

    // ── View Toggle ──────────────────────────────────────────
    setupViewToggle() {
        document.querySelectorAll('.view-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.view-toggle').forEach(b => {
                    b.classList.remove('active', 'btn-primary');
                    b.classList.add('btn-outline-primary');
                });
                btn.classList.add('active', 'btn-primary');
                btn.classList.remove('btn-outline-primary');
                toggleView(btn.dataset.view, this); 
            });
        });
    }
}

// ============================================================
// INITIALIZE APP
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const app = new JobBoardApp();
    app.init();
});