// sort_logic.js — pure sort, safe to import in worker AND main thread
export function sortJobs(jobs, sortState) {
    const { key, direction } = sortState;
    const multiplier = direction === 'asc' ? 1 : -1;
    return jobs.sort((a, b) => {
        if (key === 'salary') {
            const aVal = (a.salary && typeof a.salary.median === 'number') ? a.salary.median : null;
            const bVal = (b.salary && typeof b.salary.median === 'number') ? b.salary.median : null;
            if (aVal === null && bVal === null) return 0;
            if (aVal === null) return 1;
            if (bVal === null) return -1;
            return (aVal - bVal) * multiplier;
        }
        if (key === 'posted') {
            const aT = (a.updated_at || a.first_seen) ? Date.parse(a.updated_at || a.first_seen) : null;
            const bT = (b.updated_at || b.first_seen) ? Date.parse(b.updated_at || b.first_seen) : null;
            if (aT === null && bT === null) return 0;
            if (aT === null) return 1;
            if (bT === null) return -1;
            return (aT - bT) * multiplier;
        }
        let aVal = a[key] || '';
        let bVal = b[key] || '';
        if (key === 'location') {
            aVal = (aVal && typeof aVal === 'object') ? (aVal.name || '') : aVal;
            bVal = (bVal && typeof bVal === 'object') ? (bVal.name || '') : bVal;
        }
        if (key === 'company') {
            aVal = aVal || a.company_slug || '';
            bVal = bVal || b.company_slug || '';
        }
        aVal = (aVal == null ? '' : aVal).toString().trim().toLowerCase();
        bVal = (bVal == null ? '' : bVal).toString().trim().toLowerCase();
        if (!aVal && !bVal) return 0;
        if (!aVal) return 1;
        if (!bVal) return -1;
        if (aVal < bVal) return -1 * multiplier;
        if (aVal > bVal) return 1 * multiplier;
        return 0;
    });
}