/**
 * Job Detail Modal Component — Cyber HUD Theme
 * Displays rich posting details: Released Date, Web Scraped Timestamp, Matched Keywords Matrix, 7-factor score breakdown, and verified links.
 */

export function openJobDetailModal(job, onTrack) {
  let modal = document.getElementById('job-detail-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'job-detail-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const required = job.required_skills || [];
  const preferred = job.preferred_skills || [];
  const matched = job.tech_stack || [];
  const tips = job.improvement_tips || [];

  const score = job.overall_score || 0;
  let scoreTier = 'red';
  if (score >= 61) scoreTier = 'green';
  else if (score >= 40) scoreTier = 'purple';

  // Format dates
  const postedDateStr = job.date_posted ? new Date(job.date_posted).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recently Posted';
  const scrapedDateStr = job.date_scraped ? new Date(job.date_scraped).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Just Now';

  // Calculate days since posted for Early Application Badge
  let isEarlyOpportunity = false;
  if (job.date_posted) {
    const diffDays = Math.round((new Date() - new Date(job.date_posted)) / (1000 * 60 * 60 * 24));
    if (diffDays <= 3) isEarlyOpportunity = true;
  }

  modal.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <div class="job-company">${escapeHtml(job.company)}</div>
          <h2 class="job-title" style="font-size: 1.15rem; margin-top: 0.15rem;">${escapeHtml(job.title)}</h2>
          <div class="job-location" style="margin-top: 0.35rem;">
            📍 ${escapeHtml(job.location || 'US / Remote')} • ${escapeHtml(job.job_type || 'Tech Role')}
          </div>
        </div>
        <div class="score-pill-badge ${scoreTier}" style="font-size: 1.2rem; padding: 0.4rem 0.8rem;">
          <span>${score}</span>
          <span style="font-size: 0.6rem;">${escapeHtml(job.verdict || 'MATCH')}</span>
        </div>
      </div>

      <div class="modal-body">
        <!-- Early Opportunity Indicator -->
        ${isEarlyOpportunity ? `
          <div style="background: rgba(131, 245, 88, 0.15); border: 1px solid var(--accent-green); color: var(--accent-green); padding: 0.5rem 0.85rem; font-family: var(--font-mono); font-size: 0.8rem; margin-bottom: 1.25rem; font-weight: 700;">
            ⚡ EARLY APPLICATION OPPORTUNITY — Posted recently (${postedDateStr}). Apply early for peak visibility!
          </div>
        ` : ''}

        <!-- Telemetry Metadata Box -->
        <div style="background: #000; border: 1px solid var(--border-purple); padding: 0.85rem; margin-bottom: 1.25rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.85rem; font-family: var(--font-mono); font-size: 0.78rem;">
          <div>
            <div style="color: var(--accent-purple); font-weight: 800;">📅 RELEASED DATE</div>
            <div style="color: #fff; margin-top: 0.15rem;">${postedDateStr}</div>
          </div>
          <div>
            <div style="color: var(--accent-purple); font-weight: 800;">⏱️ SCRAPED TIMESTAMP</div>
            <div style="color: #fff; margin-top: 0.15rem;">${scrapedDateStr}</div>
          </div>
          <div>
            <div style="color: var(--accent-purple); font-weight: 800;">🎓 REQUIRED LEVEL</div>
            <div style="color: #fff; margin-top: 0.15rem;">${escapeHtml(job.experience_level || 'Internship / Co-op')}</div>
          </div>
          <div>
            <div style="color: var(--accent-purple); font-weight: 800;">🌐 SOURCE</div>
            <div style="color: #fff; margin-top: 0.15rem;">${escapeHtml(job.source || 'Official ATS')}</div>
          </div>
        </div>

        <!-- Honest Analytical Take -->
        <div style="background: rgba(139, 75, 190, 0.1); border-left: 3px solid var(--accent-purple); padding: 0.85rem; margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--accent-purple); font-family: var(--font-mono); margin-bottom: 0.3rem;">🧠 Analytical Resume Assessment</h4>
          <p style="font-size: 0.88rem; color: var(--text-primary); line-height: 1.45;">${escapeHtml(job.honest_take || 'No qualitative analysis available yet.')}</p>
        </div>

        <!-- Matched Keywords Matrix -->
        ${matched.length ? `
          <h4 style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--accent-green); font-family: var(--font-mono); margin-bottom: 0.5rem;">🔍 Matched Skills & Keywords Found</h4>
          <div class="job-tags" style="margin-bottom: 1.25rem;">
            ${matched.map(s => `<span class="tag tag-remote">✓ ${escapeHtml(s)}</span>`).join('')}
          </div>
        ` : ''}

        <!-- Required Skills -->
        ${required.length ? `
          <h4 style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--accent-purple); font-family: var(--font-mono); margin-bottom: 0.5rem;">📋 Required Role Skills</h4>
          <div class="job-tags" style="margin-bottom: 1.25rem;">
            ${required.map(s => `<span class="tag tag-type">${escapeHtml(s)}</span>`).join('')}
          </div>
        ` : ''}

        <!-- Actionable Tips -->
        ${tips.length ? `
          <h4 style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--accent-purple); font-family: var(--font-mono); margin-bottom: 0.4rem;">💡 Recommended Resume & Profile Tips</h4>
          <ul style="padding-left: 1.1rem; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
            ${tips.map(tip => `<li style="margin-bottom: 0.3rem;">${escapeHtml(tip)}</li>`).join('')}
          </ul>
        ` : ''}

        <!-- Full Description -->
        <h4 style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--text-muted); font-family: var(--font-mono); margin-bottom: 0.4rem;">Full Job Posting Text</h4>
        <div style="white-space: pre-wrap; font-size: 0.82rem; color: var(--text-secondary); background: #000; border: 1px solid var(--border-purple); padding: 0.85rem; max-height: 220px; overflow-y: auto; font-family: var(--font-mono);">
          ${escapeHtml(job.description || 'No additional description text.')}
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-sm btn-secondary btn-close-modal">Close</button>
        <button class="btn-sm btn-secondary btn-modal-track"> Track</button>
        <a href="${escapeHtml(job.apply_url || '#')}" target="_blank" rel="noopener noreferrer" class="btn-sm btn-primary">Apply Now ↗</a>
      </div>
    </div>
  `;

  modal.classList.add('active');

  const close = () => modal.classList.remove('active');
  modal.querySelector('.btn-close-modal').onclick = close;
  modal.onclick = (e) => { if (e.target === modal) close(); };

  modal.querySelector('.btn-modal-track').onclick = () => {
    onTrack(job.id);
    close();
  };
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
