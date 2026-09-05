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

/* ---------------- Motion pass ---------------- */
(function () {
  'use strict';
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasIO = 'IntersectionObserver' in window;

  /* Staggered reveal: give each child an index for the CSS delay */
  document.querySelectorAll('.reveal-group').forEach(function (group) {
    Array.prototype.forEach.call(group.children, function (el, i) { el.style.setProperty('--i', Math.min(i, 10)); });
  });

  /* Scores count up once, on first view */
  var nums = document.querySelectorAll('.score-badge b, .score__num');
  if (nums.length && !reduceMotion && hasIO) {
    var seen = {};
    try { seen = JSON.parse(sessionStorage.getItem('scores-seen') || '{}'); } catch (e) {}
    var key = location.pathname;
    if (!seen[key]) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          io.unobserve(entry.target);
          var el = entry.target, target = parseFloat(el.textContent), start = null, dur = 700;
          if (isNaN(target)) return;
          var step = function (ts) {
            if (!start) start = ts;
            var p = Math.min(1, (ts - start) / dur), e = 1 - Math.pow(1 - p, 3);
            el.textContent = (target * e).toFixed(1);
            if (p < 1) requestAnimationFrame(step); else el.textContent = target.toFixed(1);
          };
          requestAnimationFrame(step);
          setTimeout(function () { el.textContent = target.toFixed(1); }, dur + 100); /* settles even if the tab is backgrounded */
        });
      }, { threshold: 0.6 });
      nums.forEach(function (el) { io.observe(el); });
      seen[key] = 1;
      try { sessionStorage.setItem('scores-seen', JSON.stringify(seen)); } catch (e) {}
    }
  }

  /* Section tracker: highlights the TOC link and updates the mobile rail */
  var toc = document.querySelector('.toc');
  var railLabel = document.querySelector('[data-rail] .rail__section');
  var heads = Array.prototype.slice.call(document.querySelectorAll('.prose > h2[id]'));
  if ((toc || railLabel) && heads.length) {
    var links = {}, current = null, ticking = false, railDefault = railLabel ? railLabel.textContent : '';
    if (toc) toc.querySelectorAll('a[href^="#"]').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var update = function () {
      ticking = false;
      var line = window.innerHeight * 0.3, best = null;
      for (var i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top <= line) best = heads[i]; }
      var id = best ? best.id : (toc ? heads[0].id : null);
      if (id === current) return;
      if (current && links[current]) links[current].removeAttribute('aria-current');
      current = id;
      if (id && links[id]) links[id].setAttribute('aria-current', 'true');
      if (railLabel) railLabel.textContent = best ? best.textContent : railDefault;
    };
    var onScroll = function () { if (!ticking) { ticking = true; setTimeout(update, 80); } };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  }

  /* Dek clamp toggle (phones): only shown when the text is actually clamped */
  var dek = document.querySelector('.dek[data-clamp]');
  var more = document.querySelector('.dek-more');
  if (dek && more) {
    var check = function () {
      if (dek.classList.contains('is-open')) return;
      more.hidden = !(dek.scrollHeight > dek.clientHeight + 2);
    };
    more.addEventListener('click', function () {
      var open = dek.classList.toggle('is-open');
      more.setAttribute('aria-expanded', String(open));
      more.textContent = open ? 'Show less' : 'Read more';
    });
    check();
    window.addEventListener('resize', check, { passive: true });
  }
})();
