// ============================================================
// JOBS LOADER
// ============================================================

/**
 * Fetch and decompress a single gzipped JSON file.
 * @param {string} url - Path to the .json.gz file
 * @returns {Promise<Array>} Parsed JSON array
 */
export async function fetchAndDecompress(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to load ${url}`);
    const blob = await response.blob();
    const ds = new DecompressionStream('gzip');
    const text = await new Response(blob.stream().pipeThrough(ds)).blob().then(b => b.text());
    return JSON.parse(text);
}

/**
 * Load jobs progressively: first chunk on main thread, rest via worker.
 * @param {Object} app - App instance with allJobs, filteredJobs, render(), refilter()
 * @param {string} basePath - Directory containing manifest and chunks
 */
export async function loadJobsProgressive(app, basePath = './data') {
    const manifest = await fetch(`${basePath}/jobs_manifest.json`).then(r => r.json());

    // First chunk on main thread — renders immediately
    const firstChunk = await fetchAndDecompress(`${basePath}/${manifest.chunks[0]}`);
    app.allJobs = firstChunk;
    app.filteredJobs = firstChunk;
    updateStats(app.allJobs, manifest.last_updated);
    app.render();

    if (manifest.chunks.length <= 1) return;

    // Remaining chunks via web worker
    const worker = new Worker('./js/chunkWorker.js');
    let pending = manifest.chunks.length - 1;

    worker.onmessage = ({ data: jobs }) => {
        app.allJobs.push(...jobs);
        app.refilter();
        app.render();
        updateStats(app.allJobs, manifest.last_updated);
        if (--pending === 0) worker.terminate();
    };

    manifest.chunks.slice(1).forEach(chunk => {
        worker.postMessage(`/${basePath}/${chunk}`);
    });
}

/**
 * Update the stats bar in the DOM.
 * @param {Array} jobs - The full jobs array
 * @param {string} [lastUpdated] - ISO timestamp from manifest
 */
export function updateStats(jobs, lastUpdated) {
    const companies = new Set(jobs.map(j => j.company_slug || j.company)).size;
    document.getElementById('total-jobs').textContent = jobs.length.toLocaleString();
    document.getElementById('total-companies').textContent = companies.toLocaleString();
    document.getElementById('last-updated').textContent = lastUpdated
        ? new Date(lastUpdated).toLocaleDateString()
        : new Date().toLocaleDateString();
}