/**
 * Analytics View Component
 * Renders statistical insights, market skill demand, score distributions, and scrape stats.
 */

import { API } from '../utils/api.js';
import { renderCharts } from '../utils/charts.js';

export async function renderAnalyticsView(container) {
  const stats = await API.getAnalytics();
  const scrapeStatus = await API.getScrapeStatus();

  container.innerHTML = `
    <div style="max-width: 1100px; margin: 0 auto;">
      <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        📈 Employmentmaxxing Analytics & Market Pulse
      </h2>

      <!-- Stat Cards Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.25rem; border-radius: var(--radius-md);">
          <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Total Scraped Jobs</div>
          <div style="font-size: 2rem; font-weight: 800; color: #fff; margin-top: 0.25rem;">${stats.total_jobs || 0}</div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.25rem; border-radius: var(--radius-md);">
          <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">AI Analyzed & Scored</div>
          <div style="font-size: 2rem; font-weight: 800; color: var(--accent-cyan); margin-top: 0.25rem;">${stats.total_scored || 0}</div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.25rem; border-radius: var(--radius-md);">
          <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Average Chance Score</div>
          <div style="font-size: 2rem; font-weight: 800; color: #34d399; margin-top: 0.25rem;">${stats.average_score || 0}<span style="font-size: 1rem; color: var(--text-muted);">/100</span></div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.25rem; border-radius: var(--radius-md);">
          <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Active Pipeline Apps</div>
          <div style="font-size: 2rem; font-weight: 800; color: #c084fc; margin-top: 0.25rem;">${stats.total_applications || 0}</div>
        </div>
      </div>

      <!-- Charts Section -->
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.5rem; border-radius: var(--radius-lg);">
          <h3 style="font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 1rem;">🔥 Top Required Skills in Target Roles</h3>
          <canvas id="chart-top-skills" height="180"></canvas>
        </div>

        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.5rem; border-radius: var(--radius-lg);">
          <h3 style="font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 1rem;">📊 Chance Score Distribution</h3>
          <canvas id="chart-score-dist" height="180"></canvas>
        </div>
      </div>

      <!-- System Status -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 1.5rem; border-radius: var(--radius-lg);">
        <h3 style="font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 0.75rem;">⚙️ Scraper Engine Status</h3>
        <p style="font-size: 0.9rem; color: var(--text-secondary);">
          Automatically scraping every <strong>${scrapeStatus.scrape_interval_hours || 4} hours</strong> across 4 sources:
          <span style="color: var(--accent-cyan);">${(scrapeStatus.configured_sources || []).join(', ')}</span>.
        </p>
      </div>
    </div>
  `;

  // Render Charts after DOM injection
  setTimeout(() => renderCharts(stats), 100);
}
