/**
 * Employmentmaxxing Main Application Router & State Manager — HUD Theme
 */

import { API } from './utils/api.js?v=4.0';
import { renderJobCard } from './components/jobCard.js?v=4.0';
import { renderFilters } from './components/filters.js?v=4.0';
import { openJobDetailModal } from './components/jobDetail.js?v=4.0';
import { renderTrackerView } from './components/tracker.js?v=4.0';
import { renderProfileView } from './components/profile.js?v=4.0';
import { renderAnalyticsView } from './components/analytics.js?v=4.0';

let currentFilterState = {};
let currentPage = 1;
let pageSize = 25;

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initScrapeTrigger();
  initScrapeModal();
  loadJobFeed();
});

// ── Tab Router ────────────────────────────────────────────────────────
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const tabs = document.querySelectorAll('.tab-content');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');

      navItems.forEach(n => n.classList.remove('active'));
      tabs.forEach(t => t.classList.remove('active'));

      item.classList.add('active');
      const activeEl = document.getElementById(`tab-${targetTab}`);
      if (activeEl) activeEl.classList.add('active');

      if (targetTab === 'feed') loadJobFeed();
      else if (targetTab === 'tracker') renderTrackerView(document.getElementById('tab-tracker'));
      else if (targetTab === 'profile') renderProfileView(document.getElementById('tab-profile'));
      else if (targetTab === 'analytics') renderAnalyticsView(document.getElementById('tab-analytics'));
    });
  });
}

// ── Scrape Button & Modal Controls ────────────────────────────────────
function initScrapeTrigger() {
  const btn = document.getElementById('btn-trigger-scrape');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.innerText = '⏳ RUNNING SCRAPE...';
      try {
        await API.triggerScrape();
        alert('🚀 Full scrape, link verification, and resume match scoring pipeline launched in background!');
      } catch (err) {
        alert('❌ Error executing scrape: ' + err.message);
      } finally {
        setTimeout(() => {
          btn.disabled = false;
          btn.innerText = '⚡ Execute Scrape';
        }, 5000);
      }
    });
  }
}

function initScrapeModal() {
  const modal = document.getElementById('scrape-config-modal');
  const openBtn = document.getElementById('btn-open-scrape-config');
  const closeBtn = document.getElementById('btn-close-scrape-modal');
  const runBtn = document.getElementById('btn-run-custom-scrape');

  if (openBtn && modal) {
    openBtn.onclick = () => modal.classList.add('active');
    closeBtn.onclick = () => modal.classList.remove('active');
    modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('active'); };

    runBtn.onclick = async () => {
      modal.classList.remove('active');
      await API.triggerScrape();
      alert('⚡ Custom scrape pipeline launched with updated parameters!');
    };
  }
}

// ── Job Feed ──────────────────────────────────────────────────────────
async function loadJobFeed() {
  const sidebarContainer = document.getElementById('feed-filters-sidebar');
  const gridContainer = document.getElementById('job-cards-grid');
  const countDisplay = document.getElementById('feed-job-count');

  if (sidebarContainer && !sidebarContainer.children.length) {
    currentFilterState = renderFilters(sidebarContainer, (newState) => {
      currentFilterState = newState;
      currentPage = 1; // Reset to page 1 on filter change
      fetchAndRenderFeed(gridContainer, countDisplay);
    });
  }

  fetchAndRenderFeed(gridContainer, countDisplay);
}

async function fetchAndRenderFeed(gridContainer, countDisplay) {
  if (!gridContainer) return;
  gridContainer.innerHTML = '<div style="color: var(--accent-purple); padding: 2rem; font-family: var(--font-mono);">⚡ Querying position database...</div>';

  try {
    const offset = (currentPage - 1) * pageSize;
    const queryParams = {
      ...currentFilterState,
      limit: pageSize,
      offset: offset
    };

    const data = await API.getJobs(queryParams);
    gridContainer.innerHTML = '';

    const totalJobs = data.total || 0;
    const totalPages = Math.ceil(totalJobs / pageSize) || 1;
    if (currentPage > totalPages) currentPage = totalPages;

    if (countDisplay) {
      countDisplay.innerText = `ACTIVE POSITIONS: ${data.count} ON PAGE ${currentPage} / ${totalJobs} TOTAL [US TARGETS]`;
    }

    // Render Pagination Bar Top & Bottom
    renderPaginationControls(totalPages, totalJobs);

    if (!data.jobs || data.jobs.length === 0) {
      gridContainer.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 4rem 2rem; background: var(--bg-card); border: 1px dashed var(--border-purple);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📡</div>
          <h3 style="font-size: 1.1rem; color: #fff; margin-bottom: 0.5rem; font-family: var(--font-mono);">NO POSITIONS MATCHING FILTER</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); max-width: 420px; margin: 0 auto 1.5rem auto; font-family: var(--font-mono);">
            Adjust your category checkboxes or click "Execute Scrape" to index the latest US postings.
          </p>
        </div>
      `;
      return;
    }

    data.jobs.forEach(job => {
      const card = renderJobCard(
        job,
        async (jobId) => {
          const detail = await API.getJobDetail(jobId);
          openJobDetailModal(detail, async (id) => {
            await API.createApplication(id);
            alert('📌 Position logged to Application Tracker!');
          });
        },
        async (jobId) => {
          await API.createApplication(jobId);
          alert('📌 Position logged to Application Tracker!');
        }
      );
      gridContainer.appendChild(card);
    });

  } catch (err) {
    gridContainer.innerHTML = `<div style="color: var(--accent-red); padding: 2rem; font-family: var(--font-mono);">ERROR LOADING POSITIONS: ${err.message}</div>`;
  }
}

function renderPaginationControls(totalPages, totalJobs) {
  const topContainer = document.getElementById('job-cards-pagination-top');
  const bottomContainer = document.getElementById('job-cards-pagination-bottom');

  const html = `
    <div class="hud-pagination-bar">
      <button class="hud-page-btn" id="pg-first" ${currentPage === 1 ? 'disabled' : ''}>⏮ First</button>
      <button class="hud-page-btn" id="pg-prev" ${currentPage === 1 ? 'disabled' : ''}>◀ Prev</button>
      <span class="hud-page-info">PAGE ${currentPage} / ${totalPages}</span>
      <button class="hud-page-btn" id="pg-next" ${currentPage >= totalPages ? 'disabled' : ''}>Next ▶</button>
      <button class="hud-page-btn" id="pg-last" ${currentPage >= totalPages ? 'disabled' : ''}>Last ⏭</button>
      <select class="hud-page-select" id="pg-size-select">
        <option value="25" ${pageSize === 25 ? 'selected' : ''}>25 / page</option>
        <option value="50" ${pageSize === 50 ? 'selected' : ''}>50 / page</option>
        <option value="100" ${pageSize === 100 ? 'selected' : ''}>100 / page</option>
      </select>
    </div>
  `;

  if (topContainer) topContainer.innerHTML = html;
  if (bottomContainer) bottomContainer.innerHTML = html;

  const bindEvents = (container) => {
    if (!container) return;
    const btnFirst = container.querySelector('#pg-first');
    const btnPrev = container.querySelector('#pg-prev');
    const btnNext = container.querySelector('#pg-next');
    const btnLast = container.querySelector('#pg-last');
    const selectSize = container.querySelector('#pg-size-select');

    if (btnFirst) btnFirst.onclick = () => goToPage(1);
    if (btnPrev) btnPrev.onclick = () => goToPage(currentPage - 1);
    if (btnNext) btnNext.onclick = () => goToPage(currentPage + 1);
    if (btnLast) btnLast.onclick = () => goToPage(totalPages);
    if (selectSize) selectSize.onchange = (e) => {
      pageSize = parseInt(e.target.value) || 25;
      goToPage(1);
    };
  };

  bindEvents(topContainer);
  bindEvents(bottomContainer);
}

function goToPage(page) {
  currentPage = page;
  const gridContainer = document.getElementById('job-cards-grid');
  const countDisplay = document.getElementById('feed-job-count');
  fetchAndRenderFeed(gridContainer, countDisplay);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
