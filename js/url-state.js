// ============================================================
// URL STATE MANAGEMENT
// ============================================================

/**
 * Sync current filter/sort/page state to the URL query string.
 * @param {object} filterState
 * @param {number} currentPage
 * @param {{ key: string|null, direction: string }} sortState
 */
export function updateURL(filterState, currentPage, sortState) {
    const params = new URLSearchParams();

    if (filterState.title) params.set('title', filterState.title);
    if (filterState.company) params.set('company', filterState.company);
    if (filterState.location) params.set('location', filterState.location);
    if (filterState.remoteOnly) params.set('remote', '1');
    if (filterState.status) params.set('status', filterState.status);
    if (filterState.ats) params.set('ats', filterState.ats);
    if (filterState.skill_level) params.set('skill_level', filterState.skill_level);
    if (currentPage > 1) params.set('page', currentPage.toString());

    if (sortState.key) {
        params.set('sort_key', sortState.key);
        params.set('sort_dir', sortState.direction);
    }

    const newURL = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;

    window.history.replaceState({}, '', newURL);
}

/**
 * Read filter/sort/page state from the URL and populate DOM inputs.
 * @returns {{ hasFilters: boolean, page: number }}
 */
export function loadFromURL() {
    const params = new URLSearchParams(window.location.search);

    const title = params.get('title') || '';
    const company = params.get('company') || '';
    const location = params.get('location') || '';
    const remote = params.get('remote') === '1';
    const page = parseInt(params.get('page')) || 1;
    const status = params.get('status') || '';
    const ats = params.get('ats') || '';
    const skillLevel = params.get('skill_level') || '';

    document.getElementById('filter-title').value = title;
    document.getElementById('filter-company').value = company;
    document.getElementById('filter-location').value = location;
    document.getElementById('filter-remote-only').checked = remote;
    document.getElementById('filter-status').value = status;
    document.getElementById('filter-ats').value = ats;
    document.getElementById('filter-skill-level').value = skillLevel;

    const hasFilters = !!(title || company || location || remote || status || ats || skillLevel);

    return { hasFilters, page };
}