/* =========================================
   RENT & GO — app.js
   Vehicle data (mirrors the Django database),
   geolocation "near me" and page rendering.
========================================= */

(function () {
    'use strict';

    /* -------------------------------------------------
       VEHICLE DATA
       This mirrors the Django Vehicle model so the
       static pages work instantly. When the Django
       backend is running, load() can be switched to
       fetch the /vehicles API instead.
    ------------------------------------------------- */

    const DEFAULT_VEHICLES = [
        {
            id: 1, name: 'Swift', brand: 'Maruti Suzuki', type: 'car', year: 2021,
            price: 1400, location: 'Pune', lat: 18.5204, lng: 73.8567,
            image: 'images/car-card.png', owner: 'Rahul Sharma',
            description: 'Well maintained hatchback, perfect for city drives. AC, power windows and great mileage.',
            available: true,
        },
        {
            id: 2, name: 'Creta', brand: 'Hyundai', type: 'car', year: 2022,
            price: 2200, location: 'Mumbai', lat: 19.0760, lng: 72.8777,
            image: 'images/car-card.png', owner: 'Priya Verma',
            description: 'Spacious family SUV with sunroof and all modern features.',
            available: true,
        },
        {
            id: 3, name: 'Verna', brand: 'Hyundai', type: 'car', year: 2020,
            price: 1800, location: 'Delhi', lat: 28.6139, lng: 77.2090,
            image: 'images/car-card.png', owner: 'Amit Gupta',
            description: 'The classic sedan, smooth and elegant. Leather seats, touchscreen infotainment.',
            available: true,
        },
        {
            id: 4, name: 'City', brand: 'Honda', type: 'car', year: 2023,
            price: 2100, location: 'Bangalore', lat: 12.9716, lng: 77.5946,
            image: 'images/car-card.png', owner: 'Sneha Rao',
            description: 'Premium sedan, super smooth drive. Great for long highway trips.',
            available: false,
        },
        {
            id: 5, name: 'Activa', brand: 'Honda', type: 'bike', year: 2022,
            price: 400, location: 'Mumbai', lat: 19.0760, lng: 72.8777,
            image: 'images/bike-card.png', owner: 'Kiran Patil',
            description: 'Scooter for quick city commutes. Easy to ride, low fuel cost.',
            available: true,
        },
        {
            id: 6, name: 'Classic 350', brand: 'Royal Enfield', type: 'bike', year: 2021,
            price: 800, location: 'Jaipur', lat: 26.9124, lng: 75.7873,
            image: 'images/bike-card.png', owner: 'Vikram Singh',
            description: 'The Bullet. Iconic thump, timeless look. Helmet and gloves included.',
            available: true,
        },
        {
            id: 7, name: 'Pulsar 220', brand: 'Bajaj', type: 'bike', year: 2019,
            price: 600, location: 'Hyderabad', lat: 17.3850, lng: 78.4867,
            image: 'images/bike-card.png', owner: 'Mohammed Rafi',
            description: 'Sporty commuter bike in great condition. Great mileage.',
            available: true,
        },
        {
            id: 8, name: 'Apache RTR 160', brand: 'TVS', type: 'bike', year: 2023,
            price: 700, location: 'Chennai', lat: 13.0827, lng: 80.2707,
            image: 'images/bike-card.png', owner: 'Arjun K.',
            description: 'New sports bike, digital console, ABS. For riders who love speed.',
            available: true,
        },
    ];

    function loadVehicles() {
        let stored = [];
        try {
            stored = JSON.parse(localStorage.getItem('rentgoVehicles') || '[]');
        } catch (e) { /* ignore */ }
        return DEFAULT_VEHICLES.concat(stored);
    }

    function saveVehicle(vehicle) {
        let stored = [];
        try {
            stored = JSON.parse(localStorage.getItem('rentgoVehicles') || '[]');
        } catch (e) { /* ignore */ }
        vehicle.id = Math.max(100, ...DEFAULT_VEHICLES.map(v => v.id),
                              ...stored.map(v => v.id || 0)) + 1;
        stored.push(vehicle);
        localStorage.setItem('rentgoVehicles', JSON.stringify(stored));
    }

    function getVehicle(id) {
        return loadVehicles().find(v => v.id === Number(id));
    }

    /* -------------------------------------------------
       HELPERS
    ------------------------------------------------- */

    function params() {
        return new URLSearchParams(window.location.search);
    }

    function qs(sel) {
        return document.querySelector(sel);
    }

    function haversine(lat1, lng1, lat2, lng2) {
        const toRad = d => d * Math.PI / 180;
        const dLat = toRad(lat2 - lat1);
        const dLng = toRad(lng2 - lng1);
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
        return 2 * 6371 * Math.asin(Math.sqrt(a));
    }

    function indianFormat(n) {
        return Number(n).toLocaleString('en-IN');
    }

    /* -------------------------------------------------
       GEOLOCATION
    ------------------------------------------------- */

    function getPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported.'));
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
            return a.city || a.town || a.village || a.state_district || a.county || a.state;
        } catch (e) {
            return '';
        }
    }

    async function detectLocation() {
        try {
            const pos = await getPosition();
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            const city = (await reverseGeocode(lat, lng)) || (lat.toFixed(2) + ', ' + lng.toFixed(2));
            return { lat: lat, lng: lng, city: city, ok: true };
        } catch (err) {
            return { ok: false, message: err.code === 1
                ? 'Location permission denied. Enable access to find vehicles near you.'
                : (err.message || 'Unable to detect location.') };
        }
    }

    /* -------------------------------------------------
       SEARCH NAVIGATION
    ------------------------------------------------- */

    function goSearch(e) {
        e.preventDefault();
        const type = qs('#vehicleType') ? qs('#vehicleType').value : '';
        const loc = qs('#location') ? qs('#location').value.trim() : '';
        const parts = [];
        if (type) parts.push('type=' + encodeURIComponent(type));
        if (loc) parts.push('location=' + encodeURIComponent(loc));
        window.location.href = 'vehicles.html' + (parts.length ? '?' + parts.join('&') : '');
    }

    async function goNearMe(e) {
        e.preventDefault();
        const btn = e.currentTarget;
        const original = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Locating…';
        const result = await detectLocation();
        btn.innerHTML = original;

        if (!result.ok) {
            alert(result.message);
            return;
        }

        const parts = [
            'lat=' + result.lat,
            'lng=' + result.lng,
            'location=' + encodeURIComponent(result.city),
        ];
        window.location.href = 'vehicles.html?' + parts.join('&');
    }

    /* -------------------------------------------------
       VEHICLE CARDS
    ------------------------------------------------- */

    function cardHTML(v, distance) {
        const dist = (distance !== null && distance !== undefined)
            ? '<span class="dist-pill">~' + Math.round(distance) + ' km</span>' : '';
        const typeText = v.type === 'bike' ? 'Bike' : 'Car';
        return '' +
            '<a class="v-card" href="vehicle-detail.html?id=' + v.id + '">' +
                '<div class="v-card-img">' +
                    '<img src="' + v.image + '" alt="' + v.brand + ' ' + v.name + '">' +
                    '<span class="v-type">' + typeText + '</span>' +
                    dist +
                '</div>' +
                '<div class="v-card-body">' +
                    '<h3>' + v.brand + ' ' + v.name + '</h3>' +
                    '<p class="v-loc"><i class="fa-solid fa-location-dot"></i> ' + v.location + '</p>' +
                    '<p class="v-owner"><i class="fa-solid fa-user"></i> ' + v.owner + '</p>' +
                    '<div class="v-price-row">' +
                        '<span class="v-price">₹' + indianFormat(v.price) + '<small>/day</small></span>' +
                        '<span class="v-book">Book <i class="fa-solid fa-arrow-right"></i></span>' +
                    '</div>' +
                '</div>' +
            '</a>';
    }

    function renderVehicles(container, opts) {
        opts = opts || {};
        let list = loadVehicles();

        if (opts.type && opts.type !== '') {
            list = list.filter(v => v.type === opts.type);
        }
        if (opts.location) {
            const term = opts.location.toLowerCase();
            list = list.filter(v =>
                v.location.toLowerCase().includes(term) ||
                (v.brand + ' ' + v.name).toLowerCase().includes(term));
        }
        if (opts.availableOnly) {
            list = list.filter(v => v.available);
        }

        const hasCoords = opts.lat !== undefined && opts.lng !== undefined;

        if (hasCoords) {
            list = list.map(v => {
                v._distance = haversine(opts.lat, opts.lng, v.lat, v.lng);
                return v;
            }).sort((a, b) => a._distance - b._distance);
        }

        const countEl = qs('#resultCount');
        if (countEl) countEl.textContent = list.length;

        if (!list.length) {
            container.innerHTML =
                '<div class="no-results">' +
                    '<i class="fa-solid fa-car-side"></i>' +
                    '<h3>No vehicles found</h3>' +
                    '<p>Try changing filters or add your own vehicle.</p>' +
                    '<a class="signup-btn" href="add-vehicle.html">Add your vehicle</a>' +
                '</div>';
            return;
        }

        container.innerHTML = list.map(v =>
            cardHTML(v, hasCoords ? v._distance : null)).join('');
    }

    /* -------------------------------------------------
       VEHICLES PAGE
    ------------------------------------------------- */

    function initVehiclesPage() {
        const grid = qs('#vehiclesGrid');
        if (!grid) return;

        const p = params();
        const opts = {
            type: p.get('type') || '',
            location: p.get('location') || '',
            lat: p.has('lat') && p.get('lat') !== '' ? Number(p.get('lat')) : undefined,
            lng: p.has('lng') && p.get('lng') !== '' ? Number(p.get('lng')) : undefined,
            availableOnly: true,
        };

        const typeSel = qs('#filterType');
        if (typeSel) typeSel.value = opts.type;
        const locIn = qs('#filterLocation');
        if (locIn && opts.location) locIn.value = opts.location;

        const status = qs('#geoStatus');
        if (status) {
            status.innerHTML = opts.lat !== undefined
                ? '<i class="fa-solid fa-location-crosshairs"></i> Sorted by distance from you. Showing nearby vehicles first.'
                : '';
        }

        renderVehicles(grid, opts);

        qs('#filterForm').addEventListener('submit', function (e) {
            e.preventDefault();
            const type = typeSel.value;
            const loc = locIn.value.trim();
            const parts = [];
            if (type) parts.push('type=' + encodeURIComponent(type));
            if (loc) parts.push('location=' + encodeURIComponent(loc));
            window.location.href = 'vehicles.html' + (parts.length ? '?' + parts.join('&') : '');
        });

        const nearBtn = qs('#nearMeBtn');
        if (nearBtn) nearBtn.addEventListener('click', goNearMe);

        const hint = qs('#nearMeHint');
        if (hint && opts.lat === undefined) {
            hint.style.display = 'block';
        }
    }

    /* -------------------------------------------------
       INDEX PAGE
    ------------------------------------------------- */

    function initIndexPage() {
        const searchForm = qs('#searchForm');
        if (searchForm) searchForm.addEventListener('submit', goSearch);

        const nearBtns = document.querySelectorAll('#nearBtn, #nearCategory');
        nearBtns.forEach(function (btn) {
            btn.addEventListener('click', goNearMe);
        });
    }

    /* -------------------------------------------------
       DETAIL PAGE
    ------------------------------------------------- */

    function initDetailPage() {
        const root = qs('#detailRoot');
        if (!root) return;

        const v = getVehicle(params().get('id'));
        const note = qs('#bookingNote');

        if (!v) {
            root.innerHTML =
                '<div class="no-results">' +
                    '<i class="fa-solid fa-car-side"></i>' +
                    '<h3>Vehicle not found</h3>' +
                    '<a class="signup-btn" href="vehicles.html">Browse vehicles</a>' +
                '</div>';
            return;
        }

        root.innerHTML =
            '<div class="v-detail-img">' +
                '<img src="' + v.image + '" alt="' + v.brand + ' ' + v.name + '">' +
                '<span class="v-type">' + (v.type === 'bike' ? 'Bike' : 'Car') + '</span>' +
            '</div>' +
            '<div class="v-detail-body">' +
                '<h2>' + v.brand + ' ' + v.name + '</h2>' +
                '<p class="v-loc"><i class="fa-solid fa-location-dot"></i> ' + v.location + '</p>' +
                '<div class="v-detail-meta">' +
                    '<span><i class="fa-solid fa-calendar-days"></i> Model ' + v.year + '</span>' +
                    '<span><i class="fa-solid fa-user"></i> ' + v.owner + '</span>' +
                    '<span><i class="fa-solid fa-circle-check"></i> ' +
                        (v.available ? 'Available now' : 'Not available') + '</span>' +
                '</div>' +
                '<div class="v-detail-price">₹' + indianFormat(v.price) + '<small>/day</small></div>' +
                '<h3 class="v-about">About this vehicle</h3>' +
                '<p class="v-desc">' + v.description + '</p>' +
                '<div class="v-actions">' +
                    '<button class="primary-btn" id="bookBtn"><i class="fa-solid fa-calendar-check"></i> Book This Vehicle</button>' +
                    '<button class="primary-btn outline" id="contactBtn"><i class="fa-solid fa-phone"></i> Contact Owner</button>' +
                '</div>' +
                '<p id="bookingNote" class="booking-note" style="display:none;">' +
                    'Booking request feature is coming soon. Please contact the owner directly.' +
                '</p>' +
            '</div>';

        qs('#bookBtn').addEventListener('click', function () {
            note.style.display = 'block';
        });
        qs('#contactBtn').addEventListener('click', function () {
            note.style.display = 'block';
        });
    }

    /* -------------------------------------------------
       ADD VEHICLE PAGE
    ------------------------------------------------- */

    function initAddPage() {
        const form = qs('#addVehicleForm');
        if (!form) return;

        qs('#locateBtn').addEventListener('click', async function (e) {
            e.preventDefault();
            const btn = e.currentTarget;
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Locating…';
            const result = await detectLocation();
            btn.innerHTML = original;

            if (!result.ok) {
                alert(result.message);
                return;
            }

            qs('#id_location').value = result.city;
            qs('#id_latitude').value = result.lat;
            qs('#id_longitude').value = result.lng;
            qs('#locateStatus').textContent = 'Location set: ' + result.city;
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const vehicle = {
                id: 0,
                name: qs('#id_name').value.trim(),
                brand: qs('#id_brand').value.trim(),
                type: qs('#id_type').value,
                year: Number(qs('#id_year').value),
                price: Number(qs('#id_price').value),
                location: qs('#id_location').value.trim(),
                lat: Number(qs('#id_latitude').value || 0),
                lng: Number(qs('#id_longitude').value || 0),
                image: qs('#id_image').value.trim() || 'images/car-card.png',
                owner: 'You',
                description: qs('#id_description').value.trim(),
                available: qs('#id_available').checked,
            };

            if (!vehicle.name || !vehicle.brand || !vehicle.location || !vehicle.price) {
                alert('Please fill name, brand, location and price.');
                return;
            }

            saveVehicle(vehicle);
            window.location.href = 'vehicles.html';
        });
    }

    /* -------------------------------------------------
       INIT
    ------------------------------------------------- */

    function init() {
        const page = document.body.getAttribute('data-page');

        if (page === 'index') initIndexPage();
        if (page === 'vehicles') initVehiclesPage();
        if (page === 'detail') initDetailPage();
        if (page === 'add') initAddPage();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();