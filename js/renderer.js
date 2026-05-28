// ============================================================
// RENDERER
// ============================================================

import { applySorting, updateSortIndicators } from './sorting.js';
import { updatePagination } from './pagination.js';

/**
 * Render the job table for the current page.
 * @param {object} app - The JobBoardApp instance (state holder)
 */
export function render(app) {
    const tbody = document.getElementById('jobs-body');

    // Apply sorting to filtered jobs
    const displayJobs = applySorting(app.filteredJobs, app.sortState);
    const totalPages = Math.ceil(displayJobs.length / app.perPage);

    // Bounds check
    if (app.currentPage > totalPages && totalPages > 0) app.currentPage = 1;
    if (app.currentPage < 1) app.currentPage = 1;

    const start = (app.currentPage - 1) * app.perPage;
    const end = start + app.perPage;
    const pageJobs = displayJobs.slice(start, end);

    // Clear table
    tbody.innerHTML = '';

    if (pageJobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No jobs found</td></tr>';
        updatePagination(app.currentPage, 1, app.filteredJobs.length);
        updateSortIndicators(app.columns, app.sortState);
        return;
    }

    // Render rows
    pageJobs.forEach(job => {
        const row = tbody.insertRow();

        app.columns.forEach(col => {
            const cell = row.insertCell();
            cell.setAttribute('data-label', col.label);

            if (col.render) {
                cell.innerHTML = col.render(job);
            } else {
                let value = job[col.key];

                if (col.key === 'location') {
                    if (value && typeof value === 'object') {
                        value = value.name || 'Not specified';
                    } else {
                        value = value || 'Not specified';
                    }
                }

                if (col.key === 'company') {
                    value = value || job.company_slug || 'Unknown';
                }

                cell.textContent = value || 'Not specified';
            }
        });
    });

    updatePagination(app.currentPage, totalPages, app.filteredJobs.length);
    updateSortIndicators(app.columns, app.sortState);
}