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
    if (filterState.salary) params.set('salary', filterState.salary)
    if (filterState.remoteOnly) params.set('remote', '1');
    if (filterState.status) params.set('status', filterState.status);
    if (filterState.ats) params.set('ats', filterState.ats);
    if (filterState.skill_level) params.set('skill_level', filterState.skill_level);
    if (filterState.exclude) params.set('exclude', filterState.exclude)
    if (filterState.include) params.set('include', filterState.include)
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
    const salary = params.get('salary') || '';
    const remote = params.get('remote') === '1';
    const page = parseInt(params.get('page')) || 1;
    const status = params.get('status') || '';
    const ats = params.get('ats') || '';
    const skillLevel = params.get('skill_level') || '';
    const exclude = params.get('exclude') || '';
    const include = params.get('include') || '';

    document.getElementById('filter-title').value = title;
    document.getElementById('filter-company').value = company;
    document.getElementById('filter-location').value = location;
    document.getElementById('filter-salary-min').value = salary;
    document.getElementById('filter-remote-only').checked = remote;
    document.getElementById('filter-status').value = status;
    document.getElementById('filter-ats').value = ats;
    document.getElementById('filter-skill-level').value = skillLevel;
    document.getElementById('filter-exclude').value = exclude;
    document.getElementById('filter-include').value = include;

    const hasFilters = !!(title || company || location || salary || remote || status || ats || skillLevel || exclude || include);

    return { hasFilters, page };
}