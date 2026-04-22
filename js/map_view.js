// js/map_view.js

let mapInstance = null;
let heatLayer = null;
let appRef = null;  // keep a reference to the app so filters can trigger updates

const radiusByZoom = {
    2: 5, 3: 8, 4: 12, 5: 15,
    6: 20, 7: 22, 8: 20, 9: 18,
    10: 16, 11: 14, 12: 12, 13: 10,
};

export function initMap() {
    if (mapInstance) return mapInstance;

    mapInstance = L.map('map', {
        center: [39.8283, -98.5795],
        zoom: 5,
        minZoom: 2,
        maxZoom: 18,
        worldCopyJump: false,
    });

    mapInstance.setMaxBounds([[-85, -180], [85, 180]]);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(mapInstance);

    // Adjust heatmap radius/blur on zoom change
    mapInstance.on('zoomend', () => {
        if (!heatLayer) return;
        const zoom = mapInstance.getZoom();
        const radius = radiusByZoom[zoom] || 15;
        heatLayer.setOptions({ radius, blur: radius * 0.6 });
    });

    return mapInstance;
}

export function renderHeatmap(jobs) {
    if (!mapInstance) initMap();

    const buckets = new Map();
    for (const job of jobs) {
        if (!job.coords) continue;
        const key = `${job.coords[0]},${job.coords[1]}`;
        buckets.set(key, (buckets.get(key) || 0) + 1);
    }

    const MIN_JOBS_THRESHOLD = 75;
    const points = Array.from(buckets.entries())
        .filter(([key, count]) => count >= MIN_JOBS_THRESHOLD)
        .map(([key, count]) => {
            const [lat, lng] = key.split(',').map(Number);
            return [lat, lng, count];
        });

    if (heatLayer) {
        mapInstance.removeLayer(heatLayer);
    }

    const zoom = mapInstance.getZoom();
    const radius = radiusByZoom[zoom] || 15;

    heatLayer = L.heatLayer(points, {
        radius,
        blur: radius * 0.6,
        maxZoom: 10,
        minOpacity: 0.3,
        max: 4000,
        gradient: {
            0.1: 'blue',
            0.25: 'cyan',
            0.5: 'lime',
            0.75: 'yellow',
            1.0: 'red',
        },
    }).addTo(mapInstance);

    console.log(`Heatmap: ${points.length} locations, ${jobs.length} jobs, max=${Math.max(...points.map(p => p[2]))}`);
    console.log(`Heatmap: ${points.length} cities shown (filtered from ${buckets.size}), ${jobs.length} jobs`);
}

export function toggleView(view, app) {
    appRef = app;  // stash for later (e.g., filter updates)

    const tableView = document.getElementById('results');
    const mapView = document.getElementById('map-view');

    if (view === 'map') {
        document.body.classList.add('map-mode');
        tableView.style.display = 'none';
        mapView.style.display = 'block';

        if (!mapInstance) initMap();

        // Leaflet needs this when its container was hidden
        setTimeout(() => {
            mapInstance.invalidateSize();
            renderHeatmap(app.filteredJobs);
        }, 100);
    } else {
        document.body.classList.remove('map-mode');
        tableView.style.display = 'block';
        mapView.style.display = 'none';
    }
}

// Called from app when filters change and we're in map mode
export function isMapMode() {
    return document.body.classList.contains('map-mode');
}

export function updateHeatmapIfVisible() {
    if (isMapMode() && appRef) {
        renderHeatmap(appRef.filteredJobs);
    }
}