/**
 * Filter Sidebar Component — Cyber HUD Theme
 * Supports Company Tier filtering (Top 10, Top 20, Top 50, Startups),
 * Released Date vs Scraped Date sorting, multi-category checkboxes, and level filters.
 */

export function renderFilters(container, onFilterChange) {
  let searchTimeout = null;

  container.innerHTML = `
    <div class="filter-group">
      <div class="filter-title">SEARCH POSITIONS</div>
      <input type="text" class="search-input" id="filter-search" placeholder="Title, tech stack, company...">
    </div>

    <!-- Company Tier Filter -->
    <div class="filter-group">
      <div class="filter-title">COMPANY TIER</div>
      <select class="filter-select" id="filter-company-tier">
        <option value="">All Companies (1,800+ US Roles)</option>
        <option value="top_10">🏆 Top 10 Tech (FAANG / OpenAI / Stripe)</option>
        <option value="top_20">⭐ Top 20 Tech & Big AI Leaders</option>
        <option value="top_50">💎 Top 50 Unicorns & Tech Giants</option>
        <option value="startups">🚀 Startups Only (YC / VC Portfolio)</option>
      </select>
    </div>

    <!-- Multi-select Categories Checkboxes -->
    <div class="filter-group">
      <div class="filter-title">JOB CATEGORIES</div>
      <div class="checkbox-group" id="filter-categories">
        <label class="checkbox-label">
          <input type="checkbox" value="AI/ML" checked> 🤖 AI / Machine Learning
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="SWE" checked> 💻 Software Engineering
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="Quantum" checked> ⚛️ Quantum Computing
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="Data Science" checked> 📊 Data Science & Analytics
        </label>
      </div>
    </div>

    <!-- Multi-select Experience Levels Checkboxes -->
    <div class="filter-group">
      <div class="filter-title">EXPERIENCE LEVEL</div>
      <div class="checkbox-group" id="filter-levels">
        <label class="checkbox-label">
          <input type="checkbox" value="intern" checked> 🎓 Internship
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="co-op" checked> 🔄 Co-op
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="new_grad" checked> 🚀 Entry-Level / New Grad
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="full_time" checked> 💼 Full-Time SWE / Engineer
        </label>
      </div>
    </div>

    <!-- Sorting -->
    <div class="filter-group">
      <div class="filter-title">SORT ORDER</div>
      <select class="filter-select" id="filter-sort">
        <option value="earliest_release">Earliest Released Date (Newest Posted)</option>
        <option value="highest_match">Highest Resume Match Score</option>
        <option value="date_scraped">Most Recently Web Scraped</option>
        <option value="company">Company Name (A-Z)</option>
      </select>
    </div>

    <!-- Score Tier -->
    <div class="filter-group" style="border-bottom: none;">
      <div class="filter-title">MIN RESUME SCORE</div>
      <select class="filter-select" id="filter-min-score">
        <option value="">All Match Scores (0-100)</option>
        <option value="80">💎 80+ Safety Match</option>
        <option value="60">🟢 60+ Strong Match</option>
        <option value="30">🟡 30+ Worth a Shot</option>
      </select>
    </div>
  `;

  const getSelectedCheckboxes = (groupId) => {
    const checked = container.querySelectorAll(`#${groupId} input[type="checkbox"]:checked`);
    return Array.from(checked).map(cb => cb.value);
  };

  const getFilterState = () => ({
    search: container.querySelector('#filter-search').value.trim(),
    company_tier: container.querySelector('#filter-company-tier').value,
    job_types: getSelectedCheckboxes('filter-categories').join(','),
    experience_levels: getSelectedCheckboxes('filter-levels').join(','),
    sort_by: container.querySelector('#filter-sort').value,
    min_score: container.querySelector('#filter-min-score').value,
    max_days_old: 30,
  });

  container.querySelector('#filter-search').addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => onFilterChange(getFilterState()), 300);
  });

  container.querySelector('#filter-company-tier').addEventListener('change', () => onFilterChange(getFilterState()));
  container.querySelectorAll('#filter-categories input, #filter-levels input').forEach(cb => {
    cb.addEventListener('change', () => onFilterChange(getFilterState()));
  });
  container.querySelector('#filter-sort').addEventListener('change', () => onFilterChange(getFilterState()));
  container.querySelector('#filter-min-score').addEventListener('change', () => onFilterChange(getFilterState()));

  return getFilterState();
}
