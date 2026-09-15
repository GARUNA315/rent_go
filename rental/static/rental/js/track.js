/* =====================================================
        Rent&Go — GPS live tracking page (Leaflet)
===================================================== */
(function () {
    'use strict';

    var page = document.querySelector('.track-page');
    if (!page) return;

    var csrf = page.dataset.csrf;
    var updatesUrl = page.dataset.updatesUrl;
    var reportUrl = page.dataset.reportUrl;
    var tripId = page.dataset.tripId;

    var map = null;
    var trail = [];
    var routeLine = null;
    var vehicleMarker = null;
    var polyHistoryCutoff = 120; // only draw the last N points
    var lastPointCount = 0;
    var simHandle = null;
    var simIndex = 0;
    var simRoute = [];

    function el(id) { return document.getElementById(id); }

    function postPing(lat, lng, opts) {
        opts = opts || {};
        return fetch(reportUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf
            },
            body: JSON.stringify({
                trip: tripId,
                lat: lat,
                lng: lng,
                speed: opts.speed || 0,
                heading: opts.heading || 0,
                accuracy: opts.accuracy || 0,
                source: opts.source || 'gps'
            })
        }).then(function (r) {
            return r.json();
        });
    }

    function fmtTime(iso) {
        if (!iso) return '—';
        var d = new Date(iso);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function applyUpdate(u) {
        var lat = parseFloat(u.lat);
        var lng = parseFloat(u.lng);

        if (vehicleMarker) {
            vehicleMarker.setLatLng([lat, lng]);
        } else {
            vehicleMarker = L.marker([lat, lng]).addTo(map);
            map.setView([lat, lng], 15);
        }

        trail.push([lat, lng]);
        if (trail.length > polyHistoryCutoff) trail.shift();

        if (routeLine) map.removeLayer(routeLine);
        if (trail.length > 1) {
            routeLine = L.polyline(trail, {
                color: '#f75e2b',
                weight: 4,
                opacity: 0.85,
                dashArray: '6 6'
            }).addTo(map);
        }

        el('statTime').textContent = fmtTime(u.at);
        el('statSpeed').textContent = (Math.round(parseFloat(u.speed) * 10) / 10) + ' km/h';
        el('statSource').textContent = u.source === 'simulated' ? 'Demo' : 'GPS device';
        el('statPoints').textContent = (parseFloat(u.lat).toFixed(4)) + ', ' + (parseFloat(u.lng).toFixed(4));
        lastPointCount = parseInt(u.index || 0, 10);

        document.querySelectorAll('#deltaDots span').forEach(function (dot) {
            dot.classList.remove('active');
        });
    }

    function refreshTrail() {
        fetch(updatesUrl)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok || !data.updates || !data.updates.length) return;
                var latest = data.updates[data.updates.length - 1];
                var index = (data.count || 0) - data.updates.length + 1;
                applyUpdate({
                    lat: latest.lat,
                    lng: latest.lng,
                    at: latest.at,
                    speed: latest.speed,
                    source: latest.source,
                    index: index
                });
            })
            .catch(function () { /* ignore transient errors */ });
    }

    function buildSimRoute(centerLat, centerLng) {
        var route = [];
        var waypoints = [
            [0, 0], [0.002, 0.001], [0.004, -0.001], [0.007, 0.0015],
            [0.009, 0.0005], [0.012, -0.001], [0.014, 0.002], [0.017, 0.001]
        ];
        waypoints.forEach(function (wp) {
            route.push([centerLat + wp[0], centerLng + wp[1]]);
        });
        // return leg
        for (var i = waypoints.length - 2; i >= 0; i--) {
            route.push([centerLat + waypoints[i][0], centerLng + waypoints[i][1]]);
        }
        return route;
    }

    function startSim() {
        var center = [];
        if (vehicleMarker) {
            var p = vehicleMarker.getLatLng();
            center = [p.lat, p.lng];
        } else {
            center = [20.5937, 78.9629]; // default India centre
        }
        simRoute = buildSimRoute(center[0], center[1]);
        simIndex = 0;
        el('stopSimBtn').style.display = '';
        el('simulateBtn').style.display = 'none';

        simHandle = setInterval(function () {
            if (simIndex >= simRoute.length) {
                stopSim(true);
                return;
            }
            var pt = simRoute[simIndex];
            postPing(pt[0], pt[1], {
                speed: 30 + (simIndex % 5) * 12,
                heading: simIndex * 20,
                source: 'simulated'
            }).then(function (res) {
                if (res.ok) refreshTrail();
            });
            simIndex++;
        }, 900);
    }

    function stopSim(loopDone) {
        if (simHandle) clearInterval(simHandle);
        simHandle = null;
        el('stopSimBtn').style.display = 'none';
        el('simulateBtn').style.display = '';
        if (loopDone) refreshTrail();
    }

    function sendGpsPing() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported in this browser.');
            return;
        }
        var btn = el('gpsPingBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Locating…';

        navigator.geolocation.getCurrentPosition(function (pos) {
            postPing(pos.coords.latitude, pos.coords.longitude, {
                speed: pos.coords.speed || 0,
                heading: pos.coords.heading || 0,
                accuracy: pos.coords.accuracy || 0,
                source: 'gps'
            }).then(function (res) {
                if (res.ok) refreshTrail();
            }).finally(function () {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Send GPS Ping';
            });
        }, function (err) {
            alert('GPS failed: ' + (err.message || 'unable to get location'));
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Send GPS Ping';
        }, {
            enableHighAccuracy: true,
            timeout: 12000,
            maximumAge: 5000
        });
    }

    function initMap() {
        map = L.map('trackMap').setView([20.5937, 78.9629], 5);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        el('gpsPingBtn').addEventListener('click', sendGpsPing);
        el('simulateBtn').addEventListener('click', startSim);
        el('stopSimBtn').addEventListener('click', function () { stopSim(false); });

        // initial load + repeat polling
        refreshTrail();
        setInterval(refreshTrail, 4000);
    }

    function init() {
        initMap();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();