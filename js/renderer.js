// ============================================================
// RENDERER
// ============================================================

import { updateSortIndicators } from './ui_utils.js';
import { updatePagination } from './pagination.js';

/**
 * Render the job table for the current page.
 * @param {object} app - The JobBoardApp instance (state holder)
 */
export function render(app) {
    const tbody = document.getElementById('jobs-body');
    if (!tbody) return;

    let pageJobs = [];
    const totalJobsCount = app.getTotalJobsCount();
    const totalPages = Math.max(1, Math.ceil(totalJobsCount / app.perPage));

    // Bounds check
    if (app.currentPage > totalPages) app.currentPage = totalPages;
    if (app.currentPage < 1) app.currentPage = 1;

    // Pick the source: sorted snapshot if a sort is active, else the filtered set
    const sourceJobs = (app.sortState && app.sortState.key && app.sortedJobs)
        ? app.sortedJobs
        : app.filteredJobs;

    const start = (app.currentPage - 1) * app.perPage;
    pageJobs = sourceJobs.slice(start, start + app.perPage);

    tbody.innerHTML = '';
    if (pageJobs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${app.columns.length}" class="text-center">No jobs found</td></tr>`;
        updatePagination(app.currentPage, totalPages, totalJobsCount);
        return;
    }

    pageJobs.forEach(job => {
        const row = tbody.insertRow();
        app.columns.forEach(col => {
            const cell = row.insertCell();
            cell.setAttribute('data-label', col.label);
            if (col.render) {
                cell.innerHTML = col.render(job);
            } else {
                let value = job[col.key];
                if (col.key === 'location') value = value && typeof value === 'object' ? (value.name || 'Not specified') : (value || 'Not specified');
                if (col.key === 'company') value = value || job.company_slug || 'Unknown';
                cell.textContent = value || 'Not specified';
            }
        });
    });

    updatePagination(app.currentPage, totalPages, totalJobsCount);
}