// ============================================================
// FILTERING
// ============================================================

import { escapeRegex } from './ui_utils.js';
import { loadApplicationStatus } from './storage.js';

/**
 * Read current filter values from the DOM.
 * @returns {object} Filter state object
 */
export function readFilterInputs() {
    return {
        hideRecruiters: document.getElementById('filter-hide-recruiters').checked,
        remoteOnly: document.getElementById('filter-remote-only').checked,
        hideApplied: document.getElementById('filter-hide-applied').checked,
        title: document.getElementById('filter-title').value.toLowerCase().trim(),
        company: document.getElementById('filter-company').value.toLowerCase().trim(),
        location: document.getElementById('filter-location').value.toLowerCase().trim(),
        salary: document.getElementById('filter-salary-min').value,
        status: document.getElementById('filter-status').value,
        ats: document.getElementById('filter-ats').value,
        skill_level: document.getElementById('filter-skill-level').value,
        exclude: document.getElementById('filter-exclude').value.toLowerCase().trim(),
        include: document.getElementById('filter-include').value.toLowerCase().trim(),
    };
}

/**
 * Filter the full jobs array based on the current filter inputs.
 * @param {Array} allJobs - The complete jobs array
 * @returns {{ filteredJobs: Array, filterState: object }}
 */
export function filterJobs(allJobs) {
    const f = readFilterInputs();
    const apps = loadApplicationStatus();

    const titleRegex = f.title ? new RegExp(`\\b${escapeRegex(f.title)}\\b`, 'i') : null;
    const companyRegex = f.company ? new RegExp(`\\b${escapeRegex(f.company)}\\b`, 'i') : null;
    const locationRegex = f.location ? new RegExp(`\\b${escapeRegex(f.location)}\\b`, 'i') : null;

    const filterState = {
        title: f.title,
        company: f.company,
        location: f.location,
        salary: f.salary,
        remoteOnly: f.remoteOnly,
        status: f.status,
        ats: f.ats,
        skill_level: f.skill_level,
        exclude: f.exclude,
        include: f.include
    };

    const filteredJobs = allJobs.filter(job => {
        // Recruiter filter
        if (f.hideRecruiters && job.is_recruiter === true) return false;

        // Application status
        const url = job.url;
        const jobStatus = apps[url]?.status || '';

        if (f.hideApplied && (jobStatus === 'applied' || jobStatus === 'ignored')) return false;
        if (f.status && jobStatus !== f.status) return false;

        // Text fields
        const title = (job.title || '').toLowerCase();
        const company = ((job.company || job.company_slug) || '').toLowerCase();
        let location = '';
        if (job.location) {
            location = typeof job.location === 'object'
                ? (job.location.name || '').toLowerCase()
                : (job.location || '').toLowerCase();
        }

        // in your filter state collection
        const minSalary = parseInt(document.getElementById('filter-salary-min').value) || 0;

        // in filteredJobs
        if (minSalary > 0) {
            const median = job.salary?.median;
            if (!median || median < minSalary) return false;
        }

        // Remote only
        if (f.remoteOnly) {
            const isRemote = location.includes('remote')
                || (job.workplaceType && job.workplaceType.toLowerCase() === 'remote');
            if (!isRemote) return false;
        }

        // ATS
        if (f.ats) {
            const jobAts = (job.ats || '').toLowerCase();
            if (jobAts !== f.ats.toLowerCase()) return false;
        }

        // Skill level
        if (f.skill_level) {
            const jobSkillLevel = (job.skill_level || '').toLowerCase();
            if (jobSkillLevel !== f.skill_level.toLowerCase()) return false;
        }

        // Exclude title keywords
        if (f.exclude) {
            const excludeTerms = f.exclude.split(',').map(t => t.trim()).filter(Boolean);
            if (excludeTerms.some(term => title.includes(term))) return false;
        }

        // Include Title keywords
        if (f.include) {
            const includeTerms = f.include.split(',').map(t => t.trim()).filter(Boolean);
            if (!includeTerms.some(term => title.includes(term))) return false;
        }

        return (
            (!titleRegex || titleRegex.test(title)) &&
            (!companyRegex || companyRegex.test(company)) &&
            (!locationRegex || locationRegex.test(location))
        );
    });

    return { filteredJobs, filterState };
}

/** Reset all filter DOM inputs to defaults */
export function clearFilterInputs() {
    document.getElementById('filter-title').value = '';
    document.getElementById('filter-company').value = '';
    document.getElementById('filter-location').value = '';
    document.getElementById('filter-salary-min').value = '';
    document.getElementById('filter-exclude').value = '';
    document.getElementById('filter-include').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-ats').value = '';
    document.getElementById('filter-skill-level').value = '';
    document.getElementById('filter-hide-recruiters').checked = true;
    document.getElementById('filter-remote-only').checked = false;
    document.getElementById('filter-hide-applied').checked = false;
}