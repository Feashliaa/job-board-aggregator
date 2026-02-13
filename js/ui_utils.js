// ============================================================
// UI UTILITIES
// ============================================================

/** Safe HTML escaping */
export function escape(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str.toString();
    return div.innerHTML;
}

/** Escape special regex characters */
export function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Show a loading toast with spinner — returns { hide } controller */
export function showLoadingToast(message = 'Loading, please wait...') {
    const toastEl = document.getElementById('job-toast');
    const body = document.getElementById('toast-message');
    if (!toastEl) return { hide: () => { } };

    toastEl.classList.remove('show');
    toastEl.offsetHeight; // force reflow

    const existingInstance = bootstrap.Toast.getInstance(toastEl);
    if (existingInstance) {
        try { existingInstance.dispose(); } catch { }
    }

    toastEl.className = 'toast align-items-center text-white bg-secondary border-0';
    body.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <div class="spinner-border spinner-border-sm text-light" role="status"></div>
            <span>${message}</span>
        </div>`;

    const toastInstance = bootstrap.Toast.getOrCreateInstance(toastEl, { autohide: false });
    toastInstance.show();

    return {
        hide: () => {
            const instance = bootstrap.Toast.getInstance(toastEl);
            if (instance && toastEl.classList.contains('show')) instance.hide();
        }
    };
}

/** Show a dismissable toast notification */
export function showToast(message, type = 'primary') {
    const toastEl = document.getElementById('job-toast');
    const body = document.getElementById('toast-message');
    if (!toastEl) return { hide: () => { } };

    toastEl.classList.remove('show');
    toastEl.offsetHeight;

    const existingInstance = bootstrap.Toast.getInstance(toastEl);
    if (existingInstance) {
        try { existingInstance.dispose(); } catch { }
    }

    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    body.textContent = message;

    const toastInstance = bootstrap.Toast.getOrCreateInstance(toastEl, { autohide: true, delay: 4000 });
    toastInstance.show();

    return {
        hide: () => {
            const instance = bootstrap.Toast.getInstance(toastEl);
            if (instance && toastEl.classList.contains('show')) instance.hide();
        }
    };
}

/** Disable/enable UI controls and set cursor */
export function setUIBusy(isBusy) {
    const controls = ['#apply-filters', '#clear-filters', '#prev-page', '#next-page'];
    controls.forEach(sel => {
        const el = document.querySelector(sel);
        if (el) el.disabled = isBusy;
    });
    document.body.style.cursor = isBusy ? 'wait' : 'default';
}

/** Show/hide the floating action button based on checkbox state */
export function updateFABVisibility() {
    const anyChecked = document.querySelectorAll('.save-checkbox:checked, .apply-checkbox:checked, .ignored-checkbox:checked').length > 0;
    const fabContainer = document.getElementById('process-fab-container');
    fabContainer.style.display = anyChecked ? 'block' : 'none';
}

/** Parse salary string into { min, max } yearly values */
export function parseSalary(salaryString) {
    if (!salaryString) return null;

    let s = salaryString.replace(/\$/g, '').replace(/,/g, '').trim().toLowerCase();

    const isHourly = s.includes('/hr');

    let parts = s.split('/')[0];
    let range = parts.split('-').map(x => x.trim());

    const convert = (val) => {
        if (!val) return null;
        if (val.includes('k')) return parseFloat(val) * 1000;
        return parseFloat(val);
    };

    let min = convert(range[0]);
    let max = convert(range[1] ?? range[0]);

    if (min == null || isNaN(min)) return null;

    if (isHourly) {
        min *= 2080;
        max *= 2080;
    }

    return { min, max };
}