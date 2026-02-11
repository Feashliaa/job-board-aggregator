// ============================================================
// PAGINATION
// ============================================================

/**
 * Update the pagination info text and button disabled states.
 * @param {number} currentPage
 * @param {number} totalPages
 * @param {number} totalJobs - Total filtered job count
 */
export function updatePagination(currentPage, totalPages, totalJobs) {
    const pageInfo = `Page ${currentPage} of ${totalPages} (${totalJobs.toLocaleString()} jobs)`;

    document.getElementById('page-info').textContent = pageInfo;
    document.getElementById('page-info-bottom').textContent = pageInfo;

    const prevBtns = [document.getElementById('prev-page'), document.getElementById('prev-page-bottom')];
    const nextBtns = [document.getElementById('next-page'), document.getElementById('next-page-bottom')];

    prevBtns.forEach(btn => btn.disabled = currentPage === 1);
    nextBtns.forEach(btn => btn.disabled = currentPage === totalPages);
}