/* AIHustleSurfer — site.js (no dependencies) */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  /* ---------------- Mobile nav ---------------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      nav.classList.toggle('is-open', !open);
      if (!open) { var first = nav.querySelector('a'); if (first) first.focus({ preventScroll: true }); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        nav.classList.remove('is-open'); toggle.setAttribute('aria-expanded', 'false'); toggle.focus();
      }
    });
  }

  /* ---------------- Scroll reveals ---------------- */
  var revealTargets = document.querySelectorAll('.reveal, .reveal-group');
  if (revealTargets.length) {
    if (reduceMotion || !('IntersectionObserver' in window)) {
      revealTargets.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { entry.target.classList.add('is-visible'); io.unobserve(entry.target); }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
      revealTargets.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------------- Cursor-reactive card spotlight ---------------- */
  if (finePointer && !reduceMotion) {
    var cards = document.querySelectorAll('.card');
    cards.forEach(function (card) {
      var raf = null;
      card.addEventListener('pointermove', function (e) {
        if (raf) return;
        raf = requestAnimationFrame(function () {
          var r = card.getBoundingClientRect();
          card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
          card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
          raf = null;
        });
      });
    });
  }

  /* ---------------- Reading progress ---------------- */
  var progress = document.querySelector('.progress');
  var article = document.querySelector('[data-article]');
  if (progress && article && !reduceMotion) {
    var ticking = false;
    var update = function () {
      var rect = article.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var done = Math.min(1, Math.max(0, -rect.top / (total > 0 ? total : 1)));
      progress.style.transform = 'scaleX(' + done.toFixed(4) + ')';
      ticking = false;
    };
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ---------------- Tools directory filter ---------------- */
  var dir = document.querySelector('[data-tools-directory]');
  if (dir) {
    var cardsList = Array.prototype.slice.call(dir.querySelectorAll('.tool-card'));
    var chips = dir.querySelectorAll('.chip[data-category]');
    var search = dir.querySelector('#tool-search');
    var sort = dir.querySelector('#tool-sort');
    var count = dir.querySelector('[data-results-count]');
    var empty = dir.querySelector('[data-empty]');
    var grid = dir.querySelector('[data-tools-grid]');
    var state = { category: 'all', q: '', sort: 'score' };

    var params = new URLSearchParams(location.search);
    if (params.get('category')) state.category = params.get('category');
    if (params.get('q')) { state.q = params.get('q'); if (search) search.value = state.q; }

    function apply() {
      var q = state.q.trim().toLowerCase();
      var visible = 0;
      cardsList.forEach(function (card) {
        var okCat = state.category === 'all' || card.dataset.category === state.category;
        var okQ = !q || card.dataset.search.indexOf(q) !== -1;
        var show = okCat && okQ;
        card.hidden = !show;
        if (show) visible++;
      });
      var sorted = cardsList.slice().sort(function (a, b) {
        if (state.sort === 'name') return a.dataset.name.localeCompare(b.dataset.name);
        if (state.sort === 'date') return b.dataset.date.localeCompare(a.dataset.date);
        return parseFloat(b.dataset.score) - parseFloat(a.dataset.score);
      });
      sorted.forEach(function (card) { grid.appendChild(card); });
      if (count) count.textContent = visible + (visible === 1 ? ' tool' : ' tools');
      if (empty) empty.hidden = visible !== 0;
      chips.forEach(function (chip) { chip.setAttribute('aria-pressed', String(chip.dataset.category === state.category)); });

      var url = new URL(location.href);
      if (state.category === 'all') url.searchParams.delete('category'); else url.searchParams.set('category', state.category);
      if (!q) url.searchParams.delete('q'); else url.searchParams.set('q', state.q);
      history.replaceState(null, '', url);
    }

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () { state.category = chip.dataset.category; apply(); });
    });
    if (search) {
      var t;
      search.addEventListener('input', function () {
        clearTimeout(t);
        t = setTimeout(function () { state.q = search.value; apply(); }, 120);
      });
    }
    if (sort) sort.addEventListener('change', function () { state.sort = sort.value; apply(); });
    apply();
  }

  /* ---------------- YouTube facade ---------------- */
  document.querySelectorAll('.player__facade[data-youtube-id]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.dataset.youtubeId;
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) + '?autoplay=1&rel=0';
      iframe.title = btn.getAttribute('aria-label') || 'Video';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.setAttribute('allowfullscreen', '');
      btn.replaceWith(iframe);
      iframe.focus();
    });
  });

  /* ---------------- Newsletter ---------------- */
  document.querySelectorAll('form[data-newsletter]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var msg = form.parentElement.querySelector('.newsletter__msg');
      var action = form.getAttribute('action') || '';
      if (!action || action === '#') {
        e.preventDefault();
        if (msg) { msg.hidden = false; msg.textContent = 'Signup is not connected yet. Add your form endpoint in content/site.json.'; }
        return;
      }
      var btn = form.querySelector('button[type="submit"]');
      if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
    });
  });
})();
