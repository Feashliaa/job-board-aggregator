// js/map_view.js

let mapInstance = null;
let heatLayer = null;
let appRef = null;
let filterOriginalParent = null;

let mapEnabled = false;

export function enableMap() {
    mapEnabled = true;
    const overlay = document.getElementById('map-loading-overlay');
    if (overlay) overlay.remove();
}

function getRadius(zoom) {
    return Math.round(3 * Math.pow(1.5, zoom - 2));
}

let markerLayer = null;

function updateMarkers(jobs) {
    if (!mapEnabled) return;
    const zoom = mapInstance.getZoom();

    if (markerLayer) {
        mapInstance.removeLayer(markerLayer);
        markerLayer = null;
    }

    const bounds = mapInstance.getBounds();
    const quality = [];
    const fallback = [];
    const seenLetters = new Set();

    for (const job of jobs) {
        if (!job.coords) continue;
        if (!bounds.contains([job.coords[0], job.coords[1]])) continue;

        const hasRealCompany = job.company &&
            !/^\d+$/.test(job.company) &&
            !/^[a-f0-9]{8,}$/i.test(job.company);
        if (!hasRealCompany) continue;

        const letter = job.company[0].toLowerCase();
        if (seenLetters.has(letter)) continue;
        seenLetters.add(letter);

        if (job.salary?.median) {
            quality.push(job);
        } else {
            fallback.push(job);
        }

        if (seenLetters.size >= 26) break;
    }

    const sample = [
        ...quality.sort(() => 0.5 - Math.random()),
        ...fallback.sort(() => 0.5 - Math.random())
    ].slice(0, 26);

    markerLayer = L.layerGroup();
    sample.forEach(job => {
        const fmt = n => '$' + (n / 1000).toFixed(0) + 'k';
        const salary = job.salary?.median
            ? `<div style="color:#555;font-size:12px;">${fmt(job.salary.p25)} - ${fmt(job.salary.p75)}</div>`
            : '';

        const companyDisplay = (job.company || '')
            .replace(/-/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());

        const popup = `
    <div class="job-popup">
        <div class="job-popup-title">${job.title || 'Unknown'}</div>
        <div class="job-popup-company">${companyDisplay || ''}</div>
        ${job.salary?.median ? `<div class="job-popup-salary">${fmt(job.salary.p25)} - ${fmt(job.salary.p75)}</div>` : ''}
        <a href="${job.url}" target="_blank" rel="noopener noreferrer" class="job-popup-apply">Apply</a>
    </div>`;
        L.marker([job.coords[0], job.coords[1]])
            .bindPopup(popup)
            .addTo(markerLayer);
    });

    markerLayer.addTo(mapInstance);
}

export function initMap() {
    if (mapInstance) return mapInstance;

    mapInstance = L.map('map', {
        center: [39.8283, -98.5795],
        zoom: 5,
        minZoom: 2,
        maxZoom: 10,
        worldCopyJump: false,
        zoomControl: false,
    });

    L.control.zoom({ position: 'topright' }).addTo(mapInstance);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        maxZoom: 19,
    }).addTo(mapInstance);

    mapInstance.setMaxBounds([[-85, -180], [85, 180]]);

    mapInstance.on('zoomend moveend', () => {
        if (!heatLayer) return;
        const zoom = mapInstance.getZoom();
        const radius = getRadius(zoom);
        heatLayer.setOptions({ radius, blur: radius * 0.8 });
        if (appRef) updateMarkers(appRef.filteredJobs);
    });

    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = () => {
        const div = L.DomUtil.create('div');
        div.innerHTML = `
            <div style="background:white;padding:10px 14px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-size:12px;line-height:1;">
                <div style="text-align:center;color:#333;margin-bottom:5px;">High</div>
                <div style="width:16px;height:120px;background:linear-gradient(to bottom,red,yellow,lime,cyan,blue);border-radius:4px;margin:0 auto 6px;"></div>
                <div style="text-align:center;color:#333;margin-top:2.5px;">Low</div>
            </div>`;
        return div;
    };
    legend.addTo(mapInstance);

    // Only add overlay if jobs aren't loaded yet
    if (!mapEnabled) {
        const overlay = document.createElement('div');
        overlay.id = 'map-loading-overlay';
        overlay.style.cssText = 'position:absolute;inset:0;z-index:2000;background:rgba(255,255,255,0.85);display:flex;align-items:center;justify-content:center;border-radius:12px;';
        overlay.innerHTML = `<div style="font-size:16px;font-weight:600;color:#555;">Loading job data...</div>`;
        document.getElementById('map-view').appendChild(overlay);
    }

    return mapInstance;
}

function stableJitter(key) {
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
        hash = (hash << 5) - hash + key.charCodeAt(i);
        hash |= 0;
    }
    const lat = ((hash & 0xFFFF) / 0xFFFF - 0.5) * 0.02;
    const lng = (((hash >> 16) & 0xFFFF) / 0xFFFF - 0.5) * 0.02;
    return [lat, lng];
}

export function renderHeatmap(jobs) {
    if (!mapInstance) initMap();

    const buckets = new Map();
    for (const job of jobs) {
        if (!job.coords) continue;
        const key = `${job.coords[0]},${job.coords[1]}`;
        buckets.set(key, (buckets.get(key) || 0) + 1);
    }

    const points = Array.from(buckets.entries())
        .filter(([, count]) => count >= 75)
        .map(([key, count]) => {
            const [lat, lng] = key.split(',').map(Number);
            const [jLat, jLng] = stableJitter(key);
            return [lat + jLat, lng + jLng, count];
        });

    if (heatLayer) mapInstance.removeLayer(heatLayer);

    const zoom = mapInstance.getZoom();
    const radius = getRadius(zoom);

    heatLayer = L.heatLayer(points, {
        radius,
        blur: radius * 0.8,
        maxZoom: 10,
        minOpacity: 0.3,
        max: 15000,
        padding: 1.0,
        gradient: {
            0.1: 'blue',
            0.25: 'cyan',
            0.5: 'lime',
            0.75: 'yellow',
            1.0: 'red',
        },
    }).addTo(mapInstance);

    if (appRef) updateMarkers(appRef.filteredJobs);
}

export function toggleView(view, app) {
    appRef = app;
    const tableView = document.getElementById('results');
    const mapView = document.getElementById('map-view');
    const filterPanel = document.querySelector('.filter-panel');

    if (view === 'map') {
        if (!filterOriginalParent) filterOriginalParent = filterPanel.parentElement;
        document.body.classList.add('map-mode');
        tableView.style.display = 'none';
        mapView.style.display = 'block';
        mapView.appendChild(filterPanel);
        if (!mapInstance) initMap();
        setTimeout(() => {
            mapInstance.invalidateSize();
            renderHeatmap(app.filteredJobs);
        }, 100);
    } else {
        document.body.classList.remove('map-mode');
        if (filterOriginalParent) {
            filterOriginalParent.insertBefore(filterPanel, tableView);
        }
        tableView.style.display = 'block';
        mapView.style.display = 'none';
    }
}

export function isMapMode() {
    return document.body.classList.contains('map-mode');
}

export function updateHeatmapIfVisible() {
    if (isMapMode() && appRef) {
        renderHeatmap(appRef.filteredJobs);
    }
}