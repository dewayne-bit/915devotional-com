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

    show(all);

    if (input) {
      input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        if (!q) { show(all); return; }
        const filtered = all.filter(d => {
          const hay = [
            d.title || '',
            (d.scriptures || []).join(' '),
            d.summary || '',
            d.date || ''
          ].join(' ').toLowerCase();
          return hay.includes(q);
        });
        show(filtered);
      });
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

  // ---------- Init ----------

  function setYear() {
    const y = $('#year');
    if (y) y.textContent = new Date().getFullYear();
  }

  async function init() {
    setYear();
    bindPrayerForm();

    // Only fetch data if we're on a page that needs it.
    const needsData =
      document.getElementById('latest-devotional') ||
      document.getElementById('archive-list');

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
      return;
    }

    renderHome(data);
    renderArchive(data);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
