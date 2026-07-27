/**
 * Job Card Component — Resolve.ai Aesthetic
 * Renders minimalist technical job cards with clean badges, verified links, and tags.
 */

export function renderJobCard(job, onDetailClick, onTrackClick) {
  const card = document.createElement('div');
  card.className = 'job-card';

  const score = job.overall_score || 0;
  let scoreTier = 'red';
  if (score >= 81) scoreTier = 'diamond';
  else if (score >= 61) scoreTier = 'green';
  else if (score >= 31) scoreTier = 'yellow';

  // Format scraped date
  let timeLabel = 'Recently';
  if (job.date_scraped) {
    const scraped = new Date(job.date_scraped);
    const diffHours = Math.round((new Date() - scraped) / (1000 * 60 * 60));
    if (diffHours <= 1) timeLabel = 'Just now';
    else if (diffHours < 24) timeLabel = `${diffHours}h ago`;
    else timeLabel = `${Math.round(diffHours / 24)}d ago`;
  }

  card.innerHTML = `
    <div class="job-card-top">
      <div style="flex:1;">
        <div class="job-company">${escapeHtml(job.company)}</div>
        <div class="job-title">${escapeHtml(job.title)}</div>
        <div class="job-location">📍 ${escapeHtml(job.location || 'US / Remote')} • ${timeLabel}</div>
      </div>
      <div class="score-pill-badge ${scoreTier}">
        <span>${score}</span>
        <span style="font-size: 0.65rem; opacity: 0.7;">MATCH</span>
      </div>
    </div>

    <div class="job-tags">
      ${job.job_type ? `<span class="tag tag-type">${escapeHtml(job.job_type)}</span>` : ''}
      ${job.is_remote ? `<span class="tag tag-remote">🌐 Remote</span>` : ''}
      ${job.experience_level ? `<span class="tag">${escapeHtml(job.experience_level.replace('_', ' '))}</span>` : ''}
    </div>

    ${job.honest_take ? `<div class="honest-snippet">"${escapeHtml(job.honest_take)}"</div>` : ''}

    <div class="card-actions">
      <button class="btn-sm btn-secondary btn-view-detail">Details</button>
      <button class="btn-sm btn-secondary btn-track-job"> Track</button>
      <a href="${escapeHtml(job.apply_url || '#')}" target="_blank" rel="noopener noreferrer" class="btn-sm btn-primary">Apply ↗</a>
    </div>
  `;

  card.querySelector('.btn-view-detail').addEventListener('click', (e) => {
    e.stopPropagation();
    onDetailClick(job.id);
  });

  card.querySelector('.btn-track-job').addEventListener('click', (e) => {
    e.stopPropagation();
    onTrackClick(job.id);
  });

  return card;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
