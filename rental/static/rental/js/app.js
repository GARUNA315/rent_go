/* =====================================================
           Rent&Go — app.js (geolocation + UI)
===================================================== */

(function () {
    'use strict';

    const GEO = 'geo';
    const LOCATION = 'location';

    function saveState(key, value) {
        try {
            sessionStorage.setItem(key, JSON.stringify(value));
        } catch (e) { /* private mode */ }
    }

    function readState(key) {
        try {
            const raw = sessionStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function el(id) {
        return document.getElementById(id);
    }

    /* -------------------------------------------------
                GEO LOCATION HELPERS
    ------------------------------------------------- */

    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser.'));
                return;
            }
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000,
            });
        });
    }

    async function reverseGeocode(lat, lng) {
        try {
            const url = 'https://nominatim.openstreetmap.org/reverse?format=json&addressdetails=1&lat=' +
                encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lng);
            const res = await fetch(url);
            const data = await res.json();
            const a = data && data.address ? data.address : {};
            const city = a.city || a.town || a.village || a.state_district || a.county || a.state;
            return city || (lat.toFixed(3) + ', ' + lng.toFixed(3));
        } catch (e) {
            return lat.toFixed(3) + ', ' + lng.toFixed(3);
        }
    }

    function pulseLocationIcon() {
        document.querySelectorAll('.fa-location-dot, .fa-location-crosshairs')
            .forEach((icon) => {
                icon.classList.remove('locating');
                void icon.offsetWidth;
                icon.classList.add('locating');
            });
    }

    function setStatus(text) {
        const status = el('geoStatus');
        if (status) status.textContent = text;
    }

    /**
     * Detect the user's location, reverse-geocode it and remember it.
     * Returns { lat, lng, city, denied }.
     */
    async function detectLocation() {
        pulseLocationIcon();
        setStatus('Detecting your location…');

        try {
            const pos = await getCurrentPosition();
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            const city = await reverseGeocode(lat, lng);

            saveState(GEO, { lat: lat, lng: lng });
            saveState(LOCATION, city);

            window.dispatchEvent(new CustomEvent('rentgo:location', {
                detail: { lat: lat, lng: lng, city: city },
            }));

            setStatus('Location detected ✓');
            return { lat: lat, lng: lng, city: city, denied: false };
        } catch (err) {
            const msg = err.code === 1
                ? 'Location permission was denied. Enable access to find vehicles near you.'
                : (err.message || 'Unable to detect your location.');
            setStatus(msg);
            window.dispatchEvent(new CustomEvent('rentgo:locationError', { detail: msg }));
            return { denied: true, message: msg };
        }
    }

    function vehiclesNearMeUrl(opts) {
        const parts = [];
        if (opts.lat) parts.push('lat=' + encodeURIComponent(opts.lat));
        if (opts.lng) parts.push('lng=' + encodeURIComponent(opts.lng));
        if (opts.location) parts.push('location=' + encodeURIComponent(opts.location));
        if (opts.type) parts.push('type=' + encodeURIComponent(opts.type));
        return (opts.base || '/vehicles/') + (parts.length ? '?' + parts.join('&') : '');
    }

    /* -------------------------------------------------
                INDEX PAGE — location buttons
    ------------------------------------------------- */

    async function goNearMe(ev) {
        if (ev) ev.preventDefault();
        const result = await detectLocation();
        if (!result.denied) {
            fillLocationBox(result);
            setTimeout(() => {
                window.location.href = vehiclesNearMeUrl({
                    lat: result.lat,
                    lng: result.lng,
                    location: result.city,
                });
            }, 400);
        } else if (el('locationText')) {
            el('locationText').textContent = result.message;
        }
    }

    function fillLocationBox(geo) {
        const text = el('locationText');
        const locInput = el('locationInput');
        const latInput = el('latInput');
        const lngInput = el('lngInput');

        if (text) text.textContent = geo.city || 'Location detected';
        if (locInput) locInput.value = geo.city || '';
        if (latInput) latInput.value = geo.lat;
        if (lngInput) lngInput.value = geo.lng;
    }

    function bindClick(ids, handler) {
        ids.forEach((id) => {
            const node = el(id);
            if (node) node.addEventListener('click', handler);
        });
    }

    /* -------------------------------------------------
                VEHICLES PAGE — near me filter
    ------------------------------------------------- */

    async function filterNearMe(ev) {
        if (ev) ev.preventDefault();
        const result = await detectLocation();
        if (result.denied) return;

        const fLat = el('fLat');
        const fLng = el('fLng');
        const fLoc = el('filterLocation');

        if (fLat) fLat.value = result.lat;
        if (fLng) fLng.value = result.lng;
        if (fLoc && !fLoc.value) fLoc.value = result.city;

        const form = el('vehicleFilterForm');
        if (form) form.submit();
    }

    /* -------------------------------------------------
                ADD VEHICLE PAGE — use my location
    ------------------------------------------------- */

    async function fillAddVehicleLocation(ev) {
        if (ev) ev.preventDefault();
        const result = await detectLocation();
        if (result.denied) return;

        const pairs = {
            'id_name': '',
            'id_location': result.city,
            'id_latitude': result.lat,
            'id_longitude': result.lng,
        };

        for (const id of ['id_location', 'id_latitude', 'id_longitude']) {
            const node = el(id);
            if (node && pairs[id] !== undefined) {
                node.value = pairs[id];
            }
        }

        const note = document.querySelector('.add-vehicle-card .near-me-btn');
        if (note) note.classList.add('located');
    }

    /* -------------------------------------------------
                AUTH PAGE — tab switching
    ------------------------------------------------- */

    function switchAuthTab(mode) {
        const panels = document.querySelectorAll('.auth-panel');
        const tabs = document.querySelectorAll('.auth-tab');
        const showLogin = mode === 'login';

        panels.forEach((panel) => panel.classList.toggle('active',
            panel.id === (showLogin ? 'authPanelLogin' : 'authPanelSignup')));
        tabs.forEach((tab) => tab.classList.toggle('active',
            tab.id === (showLogin ? 'tabLoginBtn' : 'tabSignupBtn')));

        history.replaceState(null, '', '/auth/?mode=' + (showLogin ? 'login' : 'signup'));
    }

    /* -------------------------------------------------
                DETAIL PAGE — book / contact
    ------------------------------------------------- */

    function bindDetailButtons() {
        const note = el('bookingNote');
        const showNote = () => { if (note) note.style.display = 'block'; };

        bindClick(['bookNowBtn', 'callOwnerBtn'], (ev) => {
            ev.preventDefault();
            showNote();
        });
    }

    /* -------------------------------------------------
                SEARCH FORM — carry coords on submit
    ------------------------------------------------- */

    function bindSearchForm() {
        const form = el('searchForm');
        if (!form) return;

        form.addEventListener('submit', function () {
            const stored = readState(GEO);
            if (!stored) return;

            const latInput = el('latInput');
            const lngInput = el('lngInput');
            if (latInput && !latInput.value) latInput.value = stored.lat;
            if (lngInput && !lngInput.value) lngInput.value = stored.lng;
        });
    }

    /* -------------------------------------------------
                IMAGE ERROR FALLBACK
    ------------------------------------------------- */

    function initImageFallback() {
        document.querySelectorAll('img[data-fallback]').forEach(function (img) {
            img.addEventListener('error', function onImgError() {
                img.removeEventListener('error', onImgError);
                var fb = img.getAttribute('data-fallback');
                if (fb) img.src = fb;
            });
        });
    }

    /* -------------------------------------------------
                INIT
    ------------------------------------------------- */

    function init() {
        bindClick(['heroLocationBtn', 'bookingLocationBtn', 'nearMeBtn',
                   'nearbyCategoryBtn', 'promptNearMe'], goNearMe);

        bindClick(['filterNearMe'], filterNearMe);
        bindClick(['addVehicleLocate'], fillAddVehicleLocation);

        bindDetailButtons();
        bindSearchForm();
        initImageFallback();

        window.switchAuthTab = switchAuthTab;

        const stored = readState(GEO);
        if (stored && el('searchForm')) {
            const latInput = el('latInput');
            const lngInput = el('lngInput');
            if (latInput && !latInput.value) latInput.value = stored.lat;
            if (lngInput && !lngInput.value) lngInput.value = stored.lng;

            if (el('locationText') && !el('filterLocation')) {
                el('locationText').textContent =
                    readState(LOCATION) || 'Your location';
            }
        }

        /* Pulsing animation while locating */
        const iconClicks = document.querySelectorAll('.fa-location-crosshairs.cursor-pointer, #heroLocationBtn');
        iconClicks.forEach((icon) => {
            icon.addEventListener('click', () => {
                icon.classList.add('locating');
                setTimeout(() => icon.classList.remove('locating'), 800);
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();