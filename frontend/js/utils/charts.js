/**
 * Chart.js Visualizations Wrapper
 * Renders market demand, score distribution, and application funnel charts.
 */

export function renderCharts(data) {
  // 1. Top Skills Chart
  const topSkillsCtx = document.getElementById('chart-top-skills');
  if (topSkillsCtx && data.top_skills) {
    const skills = data.top_skills.slice(0, 10);
    new Chart(topSkillsCtx, {
      type: 'bar',
      data: {
        labels: skills.map(s => s[0]),
        datasets: [{
          label: 'Postings Requiring Skill',
          data: skills.map(s => s[1]),
          backgroundColor: 'rgba(99, 102, 241, 0.7)',
          borderColor: '#6366f1',
          borderWidth: 1,
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
          y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
  }

  // 2. Score Distribution Doughnut Chart
  const distCtx = document.getElementById('chart-score-dist');
  if (distCtx && data.score_distribution) {
    const dist = data.score_distribution;
    new Chart(distCtx, {
      type: 'doughnut',
      data: {
        labels: ['💎 Safety (81+)', '🟢 Strong (61-80)', '🟡 Worth Shot (31-60)', '🔴 Reach (0-30)'],
        datasets: [{
          data: [dist.excellent || 0, dist.strong || 0, dist.moderate || 0, dist.reach || 0],
          backgroundColor: ['#a855f7', '#10b981', '#f59e0b', '#ef4444'],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#9ca3af', font: { size: 12 } } }
        }
      }
    });
  }
}
