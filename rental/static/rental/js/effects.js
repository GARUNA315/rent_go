/* =====================================================
        Rent&Go — scroll & dynamic effects engine
        scroll progress · reveal · parallax · glow ·
        back-to-top · smooth anchors · card tilt · counters
===================================================== */
(function () {
    'use strict';

    var prefersReduced = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* -------------------------------------------------
                SCROLL PROGRESS BAR
    ------------------------------------------------- */
    function initScrollProgress() {
        var bar = document.getElementById('scrollProgress');
        if (!bar) return;

        var update = function () {
            var doc = document.documentElement;
            var max = doc.scrollHeight - doc.clientHeight;
            var pct = max > 0 ? (doc.scrollTop / max) * 100 : 0;
            bar.style.width = pct + '%';
        };

        window.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update, { passive: true });
        update();
    }

    /* -------------------------------------------------
                REVEAL ON SCROLL
    ------------------------------------------------- */
    function initReveal() {
        var items = document.querySelectorAll('.reveal');
        if (!items.length) return;

        // stagger children that opt in
        document.querySelectorAll('.stagger').forEach(function (group) {
            Array.prototype.forEach.call(group.children, function (child, i) {
                child.style.transitionDelay = (i * 90) + 'ms';
            });
        });

        if (prefersReduced || !('IntersectionObserver' in window)) {
            items.forEach(function (el) { el.classList.add('visible'); });
            return;
        }

        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.14, rootMargin: '0px 0px -40px 0px' });

        items.forEach(function (el) { obs.observe(el); });
    }

    /* -------------------------------------------------
                PARALLAX LAYERS
    ------------------------------------------------- */
    function initParallax() {
        if (prefersReduced) return;

        var hero = document.querySelector('.hero');
        if (!hero) return;

        var bg = hero.querySelector('.hero-background');
        var cars = hero.querySelector('.hero-vehicles');
        var slogan = hero.querySelector('.hero-slogan');

        var ticking = false;
        var onScroll = function () {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(function () {
                var y = window.scrollY || window.pageYOffset;
                if (bg) bg.style.transform = 'translateY(' + (y * 0.25) + 'px) scale(1.05)';
                if (cars) cars.style.transform = 'translateY(' + (y * -0.12) + 'px)';
                if (slogan) slogan.style.transform = 'translateY(' + (y * 0.18) + 'px)';
                ticking = false;
            });
        };

        window.addEventListener('scroll', onScroll, { passive: true });
        initParallaxTilt();
    }

    function initParallaxTilt() {
        var layers = document.querySelectorAll('.parallax-layer');
        layers.forEach(function (layer) {
            var speed = parseFloat(layer.dataset.speed || '10');
            document.addEventListener('mousemove', function (e) {
                var cx = (e.clientX / window.innerWidth - 0.5) * 2;
                var cy = (e.clientY / window.innerHeight - 0.5) * 2;
                layer.style.transform =
                    'translate(' + (cx * speed) + 'px,' + (cy * speed) + 'px)';
            }, { passive: true });
        });
    }

    /* -------------------------------------------------
                CURSOR GLOW
    ------------------------------------------------- */
    function initMouseGlow() {
        var glow = document.getElementById('mouseGlow');
        if (!glow || prefersReduced) return;
        if (!window.matchMedia('(pointer: fine)').matches) return; // touch devices

        var raf = null;
        document.addEventListener('mousemove', function (e) {
            if (raf) return;
            raf = requestAnimationFrame(function () {
                glow.style.left = e.clientX + 'px';
                glow.style.top = e.clientY + 'px';
                glow.classList.add('active');
                raf = null;
            });
        }, { passive: true });

        document.addEventListener('mouseleave', function () {
            glow.classList.remove('active');
        });
    }

    /* -------------------------------------------------
                BACK TO TOP
    ------------------------------------------------- */
    function initBackToTop() {
        var btn = document.getElementById('backToTop');
        if (!btn) return;

        var toggle = function () {
            btn.classList.toggle('show', (window.scrollY || 0) > 500);
        };
        window.addEventListener('scroll', toggle, { passive: true });
        toggle();

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: prefersReduced ? 'auto' : 'smooth' });
        });
    }

    /* -------------------------------------------------
                SMOOTH ANCHOR SCROLLING
    ------------------------------------------------- */
    function initAnchors() {
        document.querySelectorAll('a[href^="#"]').forEach(function (link) {
            link.addEventListener('click', function (e) {
                var id = link.getAttribute('href');
                if (id.length < 2) return;
                var target = document.querySelector(id);
                if (!target) return;
                e.preventDefault();
                target.scrollIntoView({
                    behavior: prefersReduced ? 'auto' : 'smooth',
                    block: 'start',
                });
            });
        });
    }

    /* -------------------------------------------------
                CARD TILT (vehicle cards)
    ------------------------------------------------- */
    function initCardTilt() {
        if (prefersReduced || !window.matchMedia('(pointer: fine)').matches) return;

        document.querySelectorAll('.vehicle-card').forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var rect = card.getBoundingClientRect();
                var rx = (e.clientY - rect.top) / rect.height - 0.5;
                var ry = (e.clientX - rect.left) / rect.width - 0.5;
                card.style.transform =
                    'perspective(800px) rotateX(' + (-rx * 6) + 'deg) rotateY(' + (ry * 6) + 'deg)';
            });
            card.addEventListener('mouseleave', function () {
                card.style.transform = '';
            });
        });
    }

    /* -------------------------------------------------
                COUNT-UP STATS
    ------------------------------------------------- */
    function initCounters() {
        document.querySelectorAll('.stat h3, .stat-tile h3').forEach(function (node) {
            var raw = node.textContent;
            var match = raw.replace(/[.,\s]/g, '').match(/^(\d+)/);
            if (!match) return;
            var target = parseInt(match[1], 10);
            var suffix = raw.replace(/^[\d.,\s]+/, '').trim();

            var check = function () {
                var rect = node.getBoundingClientRect();
                return rect.top < window.innerHeight && rect.bottom > 0;
            };

            var done = false;
            var animate = function () {
                var start = null;
                var step = function (ts) {
                    if (!start) start = ts;
                    var p = Math.min((ts - start) / 1400, 1);
                    var eased = 1 - Math.pow(1 - p, 3);
                    var value = Math.round(target * eased);
                    node.textContent = value.toLocaleString('en-IN') + (suffix ? ' ' + suffix : '');
                    if (p < 1) requestAnimationFrame(step);
                };
                requestAnimationFrame(step);
            };

            var mark = function () {
                if (done || !check()) return;
                done = true;
                animate();
                window.removeEventListener('scroll', mark);
            };

            window.addEventListener('scroll', mark, { passive: true });
            mark();
        });
    }

    /* -------------------------------------------------
                RISK PAGE — TOC scrollspy
    ------------------------------------------------- */
    function initRiskSpy() {
        var toc = document.querySelector('.risk-toc-links');
        if (!toc) return;

        var links = toc.querySelectorAll('a[href^="#"]');
        var sections = [];
        links.forEach(function (link) {
            var node = document.querySelector(link.getAttribute('href'));
            if (node) sections.push({ link: link, section: node });
        });
        if (!sections.length) return;

        var setActive = function (id) {
            links.forEach(function (link) {
                link.classList.toggle('is-active', link.getAttribute('href') === id);
            });
        };

        var onScroll = function () {
            var pos = (window.scrollY || 0) + 140;
            var current = null;
            sections.forEach(function (item) {
                if (item.section.offsetTop <= pos) current = item;
            });
            if (current) setActive('#' + current.section.id);
        };

        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    /* -------------------------------------------------
                INIT
    ------------------------------------------------- */
    function init() {
        initScrollProgress();
        initReveal();
        initParallax();
        initMouseGlow();
        initBackToTop();
        initAnchors();
        initCardTilt();
        initCounters();
        initRiskSpy();

        // entrance animation for the hero
        var heroContent = document.querySelector('.hero-content');
        if (heroContent) {
            setTimeout(function () { heroContent.classList.add('entered'); }, 120);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();