// ============================================================
// LOCAL STORAGE UTILITIES
// ============================================================

const STORAGE_KEY = 'job-applications';

/** Load all application statuses from localStorage */
export function loadApplicationStatus() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
}

/** Save a job's application status */
export function saveApplicationStatus(jobUrl, status) {
    const apps = loadApplicationStatus();
    apps[jobUrl] = {
        status: status, // 'saved', 'applied', 'ignored'
        date: new Date().toISOString()
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(apps));
}

/** Delete a job's application status */
export function deleteApplicationStatus(jobUrl) {
    const apps = loadApplicationStatus();
    delete apps[jobUrl];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(apps));
}