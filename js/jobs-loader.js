// ============================================================
// JOBS LOADER
// ============================================================

/**
 * Fetch and decompress the gzipped jobs JSON.
 * @param {string} url - Path to the .json.gz file
 * @returns {Promise<Array>} Parsed jobs array
 */
export async function fetchJobs(url = './data/all_jobs.json.gz') {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to load jobs');

    const blob = await response.blob();
    const ds = new DecompressionStream('gzip');
    const decompressedStream = blob.stream().pipeThrough(ds);
    const decompressedBlob = await new Response(decompressedStream).blob();
    const text = await decompressedBlob.text();

    return JSON.parse(text);
}

/**
 * Update the stats bar in the DOM.
 * @param {Array} jobs - The full jobs array
 */
export function updateStats(jobs) {
    const companies = new Set(jobs.map(j => j.company_slug || j.company)).size;
    document.getElementById('total-jobs').textContent = jobs.length.toLocaleString();
    document.getElementById('total-companies').textContent = companies.toLocaleString();
    document.getElementById('last-updated').textContent = new Date().toLocaleDateString();
}