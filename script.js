/* ============================================
   9:15 Devotional — Site JS
   Loads devotionals from devotionals.json,
   renders cards, handles search & form UX.
   ============================================ */

(function() {
  'use strict';

  // ---------- Helpers ----------

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function formatDate(isoDate) {
    // isoDate: 'YYYY-MM-DD' — render as 'Wed, May 7'
    if (!isoDate) return '';
    const [y, m, d] = isoDate.split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function formatScriptures(arr) {
    if (!arr || arr.length === 0) return '';
    return arr.join(' · ');
  }

  function escapeHtml(s) {
    if (s === undefined || s === null) return '';
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function youtubeEmbedUrl(id) {
    // rel=0 keeps related videos to same channel; modestbranding reduces YT chrome.
    return `https://www.youtube.com/embed/${encodeURIComponent(id)}?rel=0&modestbranding=1`;
  }

  // ---------- Render helpers ----------

  function renderFeatured(d) {
    return `
      <div class="video-wrap">
        <iframe src="${youtubeEmbedUrl(d.youtubeId)}"
                title="${escapeHtml(d.title)}"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen
                loading="lazy"></iframe>
      </div>
      <div class="latest-meta">
        <p class="latest-date">${formatDate(d.date)}</p>
        <h3>${escapeHtml(d.title)}</h3>
        <p class="scriptures"><span class="scriptures-label">Scripture:</span> ${escapeHtml(formatScriptures(d.scriptures))}</p>
        ${d.summary ? `<p class="summary">${escapeHtml(d.summary)}</p>` : ''}
      </div>
    `;
  }

  function renderCard(d) {
    return `
      <article class="devo-card">
        <div class="video-wrap">
          <iframe src="${youtubeEmbedUrl(d.youtubeId)}"
                  title="${escapeHtml(d.title)}"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowfullscreen
                  loading="lazy"></iframe>
        </div>
        <div class="card-body">
          <p class="card-date">${formatDate(d.date)}</p>
          <h3>${escapeHtml(d.title)}</h3>
          <p class="scriptures">${escapeHtml(formatScriptures(d.scriptures))}</p>
          ${d.summary ? `<p class="summary">${escapeHtml(d.summary)}</p>` : ''}
        </div>
      </article>
    `;
  }

  // ---------- Today schedule ----------

  function todayStatus() {
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const today = new Date();
    const day = today.getDay(); // 0=Sun, 1=Mon, ...
    if (day >= 1 && day <= 4) {
      return `Yes — we meet today (${dayNames[day]}) at 9:15 AM ET.`;
    } else if (day === 5) {
      return `No devotional today (Friday). Next session: Monday at 9:15 AM ET.`;
    } else if (day === 6) {
      return `No devotional today (Saturday). Next session: Monday at 9:15 AM ET.`;
    } else {
      return `No devotional today (Sunday). Next session: Monday at 9:15 AM ET.`;
    }
  }

  // ---------- Data load ----------

  async function loadData() {
    try {
      const res = await fetch('devotionals.json', { cache: 'no-store' });
      if (!res.ok) throw new Error('failed to load devotionals.json');
      return await res.json();
    } catch (err) {
      console.error('Could not load devotionals.json:', err);
      return null;
    }
  }

  function sortedDevotionals(data) {
    if (!data || !Array.isArray(data.devotionals)) return [];
    return [...data.devotionals].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  }

  // ---------- Page: Home ----------

  function renderHome(data) {
    const list = sortedDevotionals(data);

    // Latest (featured)
    const latestEl = $('#latest-devotional');
    if (latestEl) {
      if (list.length === 0) {
        latestEl.innerHTML = '<p class="empty-state">No devotionals yet — check back soon.</p>';
      } else {
        latestEl.innerHTML = renderFeatured(list[0]);
      }
    }

    // Recent (next 6 after the latest)
    const recentEl = $('#recent-list');
    if (recentEl) {
      const recent = list.slice(1, 7);
      if (recent.length === 0) {
        recentEl.innerHTML = '<p class="empty-state">More devotionals will appear here as the archive grows.</p>';
      } else {
        recentEl.innerHTML = recent.map(renderCard).join('');
      }
    }

    // Zoom link
    const zoom = (data && data.zoom) || {};
    const zoomLink = $('#zoom-link');
    if (zoomLink && zoom.joinUrl) zoomLink.href = zoom.joinUrl;
    const zid = $('#zoom-id');
    if (zid && zoom.meetingId) zid.textContent = zoom.meetingId;
    const zpass = $('#zoom-pass');
    if (zpass && zoom.passcode) zpass.textContent = zoom.passcode;

    // Today status
    const ts = $('#today-status');
    if (ts) ts.textContent = todayStatus();
  }

  // ---------- Page: Scripture List ----------

  // Canonical Bible order — drives the grouping and sort on list.html.
  const BOOK_ORDER = [
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua',
    'Judges', 'Ruth', '1 Samuel', '2 Samuel', '1 Kings', '2 Kings',
    '1 Chronicles', '2 Chronicles', 'Ezra', 'Nehemiah', 'Esther', 'Job',
    'Psalms', 'Proverbs', 'Ecclesiastes', 'Song of Solomon', 'Isaiah',
    'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
    'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai',
    'Zechariah', 'Malachi',
    'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans', '1 Corinthians',
    '2 Corinthians', 'Galatians', 'Ephesians', 'Philippians', 'Colossians',
    '1 Thessalonians', '2 Thessalonians', '1 Timothy', '2 Timothy', 'Titus',
    'Philemon', 'Hebrews', 'James', '1 Peter', '2 Peter', '1 John', '2 John',
    '3 John', 'Jude', 'Revelation'
  ];
  const OT_COUNT = BOOK_ORDER.indexOf('Matthew');

  // "1 Peter 3:15" / "Ecclesiastes 9:10-11" / "Psalms 23"
  function parseRef(ref) {
    const m = String(ref).trim().match(/^(.+?)\s+(\d+)(?::(\d+)(?:\s*[-–]\s*(\d+))?)?$/);
    if (!m) return null;
    let book = m[1].trim();
    if (/^psalm$/i.test(book)) book = 'Psalms';
    return {
      ref: ref,
      book: book,
      chapter: parseInt(m[2], 10),
      verse: m[3] ? parseInt(m[3], 10) : 0,
      verseEnd: m[4] ? parseInt(m[4], 10) : null
    };
  }

  function slugifyBook(book) {
    return 'book-' + book.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }

  function renderScriptureList(data) {
    const listEl = $('#scripture-list');
    if (!listEl) return;

    const all = sortedDevotionals(data);
    const byBook = new Map();
    const noScripture = [];

    all.forEach(d => {
      const refs = d.scriptures || [];
      if (refs.length === 0) { noScripture.push(d); return; }
      refs.forEach(r => {
        const p = parseRef(r);
        if (!p) return;
        p.devotional = d;
        if (!byBook.has(p.book)) byBook.set(p.book, []);
        byBook.get(p.book).push(p);
      });
    });

    // Bible order; anything unrecognized falls to the end, alphabetically.
    const books = Array.from(byBook.keys()).sort((a, b) => {
      const ia = BOOK_ORDER.indexOf(a), ib = BOOK_ORDER.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });

    let passageCount = 0;
    books.forEach(b => {
      byBook.get(b).sort((x, y) => x.chapter - y.chapter || x.verse - y.verse);
      passageCount += byBook.get(b).length;
    });

    // Stats line
    const stats = $('#list-stats');
    if (stats) {
      stats.innerHTML =
        `<strong>${passageCount}</strong> passage${passageCount === 1 ? '' : 's'} · ` +
        `<strong>${books.length}</strong> book${books.length === 1 ? '' : 's'} · ` +
        `<strong>${all.length}</strong> devotional${all.length === 1 ? '' : 's'}`;
    }

    // Jump links
    const jump = $('#book-jump');
    if (jump) {
      jump.innerHTML = books.map(b =>
        `<a href="#${slugifyBook(b)}" class="jump-chip">${escapeHtml(b)} <span>${byBook.get(b).length}</span></a>`
      ).join('');
    }

    if (books.length === 0) {
      listEl.innerHTML = '<p class="empty-state">No scriptures logged yet — check back soon.</p>';
      return;
    }

    let html = '';
    let testamentOpen = null;

    books.forEach(b => {
      const idx = BOOK_ORDER.indexOf(b);
      const testament = idx === -1 ? 'Other' : (idx < OT_COUNT ? 'Old Testament' : 'New Testament');
      if (testament !== testamentOpen) {
        if (testamentOpen !== null) html += '</div>';
        html += `<div class="testament-block"><h2 class="testament-head">${testament}</h2>`;
        testamentOpen = testament;
      }

      const rows = byBook.get(b).map(p => {
        const d = p.devotional;
        const verse = p.verse
          ? `${p.chapter}:${p.verse}${p.verseEnd ? '–' + p.verseEnd : ''}`
          : `Chapter ${p.chapter}`;
        const showTitle = d.title && d.title !== p.ref;
        return `
          <li class="verse-row">
            <a class="verse-link" href="devotionals.html?q=${encodeURIComponent(p.ref)}">
              <span class="verse-ref">${escapeHtml(verse)}</span>
              <span class="verse-meta">
                ${showTitle ? `<span class="verse-title">${escapeHtml(d.title)}</span>` : ''}
                <span class="verse-date">${formatDate(d.date)}</span>
              </span>
            </a>
          </li>`;
      }).join('');

      html += `
        <section class="book-block" id="${slugifyBook(b)}">
          <h3 class="book-head">${escapeHtml(b)} <span class="book-count">${byBook.get(b).length}</span></h3>
          <ul class="verse-list">${rows}</ul>
        </section>`;
    });
    if (testamentOpen !== null) html += '</div>';

    if (noScripture.length) {
      html += `
        <section class="book-block other-block">
          <h3 class="book-head">Other Devotionals <span class="book-count">${noScripture.length}</span></h3>
          <p class="book-note">Not tied to a single passage.</p>
          <ul class="verse-list">
            ${noScripture.map(d => `
              <li class="verse-row">
                <a class="verse-link" href="devotionals.html?q=${encodeURIComponent(d.title)}">
                  <span class="verse-ref verse-ref-wide">${escapeHtml(d.title)}</span>
                  <span class="verse-meta"><span class="verse-date">${formatDate(d.date)}</span></span>
                </a>
              </li>`).join('')}
          </ul>
        </section>`;
    }

    listEl.innerHTML = html;
  }

  // ---------- Page: Archive ----------

  function renderArchive(data) {
    const listEl = $('#archive-list');
    if (!listEl) return;

    const all = sortedDevotionals(data);
    const countEl = $('#search-count');
    const input = $('#search-input');

    function show(filtered) {
      if (filtered.length === 0) {
        listEl.innerHTML = '<p class="empty-state">No devotionals match that search.</p>';
      } else {
        listEl.innerHTML = filtered.map(renderCard).join('');
      }
      if (countEl) {
        countEl.textContent = filtered.length === all.length
          ? `${all.length} devotional${all.length === 1 ? '' : 's'}`
          : `${filtered.length} of ${all.length} match`;
      }
    }

    if (all.length === 0) {
      listEl.innerHTML = '<p class="empty-state">No devotionals yet — check back soon.</p>';
      if (countEl) countEl.textContent = '';
      return;
    }

    function filterBy(q) {
      const needle = q.trim().toLowerCase();
      if (!needle) { show(all); return; }
      const filtered = all.filter(d => {
        const hay = [
          d.title || '',
          (d.scriptures || []).join(' '),
          d.summary || '',
          d.date || ''
        ].join(' ').toLowerCase();
        return hay.includes(needle);
      });
      show(filtered);
    }

    // Arriving from the scripture list: devotionals.html?q=1+Peter+3:15
    let initial = '';
    try {
      initial = new URLSearchParams(window.location.search).get('q') || '';
    } catch (e) { /* older browser — no deep link, no problem */ }

    if (initial) {
      if (input) input.value = initial;
      filterBy(initial);
    } else {
      show(all);
    }

    if (input) {
      input.addEventListener('input', () => filterBy(input.value));
    }
  }

  // ---------- Page: Prayer form ----------

  function bindPrayerForm() {
    const form = $('#prayer-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      // If still pointing at the placeholder, don't actually submit — let user know.
      if (form.action.includes('YOUR_FORM_ID')) {
        e.preventDefault();
        alert('Heads up: the prayer form needs to be connected to Formspree before it can send. See README.md → "Step 3: Connect the prayer form."');
        return;
      }

      e.preventDefault();
      const success = $('#form-success');
      const data = new FormData(form);
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: data,
          headers: { 'Accept': 'application/json' }
        });
        if (res.ok) {
          form.classList.add('hidden');
          if (success) success.classList.remove('hidden');
        } else {
          const json = await res.json().catch(() => ({}));
          alert(json.error || 'Something went wrong submitting your request. Please try again or email dewayne@shingleusa.com directly.');
        }
      } catch (err) {
        alert('Network error. Please try again, or email dewayne@shingleusa.com directly.');
      }
    });
  }

  // ---------- Scripture suggestion form (home hero) ----------

  function bindScriptureForm() {
    const form = $('#scripture-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const success = $('#scripture-success');
      const btn = form.querySelector('button[type="submit"]');
      const data = new FormData(form);
      if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: data,
          headers: { 'Accept': 'application/json' }
        });
        if (res.ok) {
          form.classList.add('hidden');
          if (success) success.classList.remove('hidden');
        } else {
          const json = await res.json().catch(() => ({}));
          alert(json.error || 'Something went wrong sending your suggestion. Please try again or email dewayne@shingleusa.com directly.');
        }
      } catch (err) {
        alert('Network error. Please try again, or email dewayne@shingleusa.com directly.');
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Send Suggestion'; }
      }
    });
  }

  // ---------- Init ----------

  function setYear() {
    const y = $('#year');
    if (y) y.textContent = new Date().getFullYear();
  }

  async function init() {
    setYear();
    bindPrayerForm();
    bindScriptureForm();

    // Only fetch data if we're on a page that needs it.
    const needsData =
      document.getElementById('latest-devotional') ||
      document.getElementById('archive-list') ||
      document.getElementById('scripture-list');

    if (!needsData) return;

    const data = await loadData();
    if (!data) {
      // Show fallback messages
      const latestEl = $('#latest-devotional');
      if (latestEl) latestEl.innerHTML = '<p class="empty-state">Could not load devotionals. Make sure devotionals.json is in the same folder.</p>';
      const recentEl = $('#recent-list');
      if (recentEl) recentEl.innerHTML = '';
      const archiveEl = $('#archive-list');
      if (archiveEl) archiveEl.innerHTML = '<p class="empty-state">Could not load devotionals.</p>';
      const listEl = $('#scripture-list');
      if (listEl) listEl.innerHTML = '<p class="empty-state">Could not load the scripture list.</p>';
      return;
    }

    renderHome(data);
    renderArchive(data);
    renderScriptureList(data);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
