// ============================================================
// SORTING
// 
// This module is likely to not be used in the future, as
// the it seems rather redundant, and instead we can just focus
// on filtering and pagination.
// ============================================================

/**
 * Sort jobs array in place based on the given sort state.
 * @param {Array} jobs - The jobs array to sort
 * @param {{ key: string|null, direction: 'asc'|'desc' }} sortState
 * @returns {Array} The sorted array (same reference)
 */
export function applySorting(jobs, sortState) {
    if (!sortState.key) return jobs;

    const { key, direction } = sortState;
    const multiplier = direction === 'asc' ? 1 : -1;

    return jobs.sort((a, b) => {
        let aVal = a[key] || '';
        let bVal = b[key] || '';

        // Handle location object
        if (key === 'location') {
            if (aVal && typeof aVal === 'object') aVal = aVal.name || '';
            if (bVal && typeof bVal === 'object') bVal = bVal.name || '';
        }

        // Handle company_slug fallback
        if (key === 'company') {
            aVal = aVal || a.company_slug || '';
            bVal = bVal || b.company_slug || '';
        }

        aVal = aVal.toString().toLowerCase();
        bVal = bVal.toString().toLowerCase();

        // Push numeric-leading strings after alpha
        const aStartsWithNumber = /^\d/.test(aVal);
        const bStartsWithNumber = /^\d/.test(bVal);
        if (aStartsWithNumber && !bStartsWithNumber) return 1;
        if (!aStartsWithNumber && bStartsWithNumber) return -1;

        return aVal < bVal ? -multiplier : aVal > bVal ? multiplier : 0;
    });
}

/**
 * Update the visual sort indicators on table headers.
 * @param {Array} columns - Column definitions
 * @param {{ key: string|null, direction: 'asc'|'desc' }} sortState
 */
export function updateSortIndicators(columns, sortState) {
    document.querySelectorAll('.job-table thead th').forEach((th, index) => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const column = columns[index];

        if (column && column.key === sortState.key) {
            th.classList.add(
                sortState.direction === 'asc' ? 'sorted-asc' : 'sorted-desc'
            );
        }
    });
}