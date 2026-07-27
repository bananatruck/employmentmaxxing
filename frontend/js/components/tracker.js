/**
 * Application Tracker (Kanban Board) Component
 * Drag-and-drop Kanban board across 6 stages:
 * Interested -> Applied -> Screening -> Interview -> Offer -> Rejected
 */

import { API } from '../utils/api.js';

const STAGES = [
  { id: 'interested', label: '📌 Interested' },
  { id: 'applied', label: '🚀 Applied' },
  { id: 'screening', label: '📞 Screening' },
  { id: 'interview', label: '💬 Interview' },
  { id: 'offer', label: '🎉 Offer' },
  { id: 'rejected', label: '❌ Rejected' },
];

export async function renderTrackerView(container) {
  const apps = await API.getApplications();

  container.innerHTML = `
    <div style="margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h2 style="font-size: 1.5rem; font-weight: 800; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
          📊 Application Tracking Pipeline
        </h2>
        <p style="font-size: 0.9rem; color: var(--text-secondary);">
          Track your application stages. Drag and drop cards to update status.
        </p>
      </div>
      <div style="font-size: 0.9rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border-glass);">
        Total Active Applications: <strong style="color: #fff;">${apps.length}</strong>
      </div>
    </div>

    <div class="kanban-board">
      ${STAGES.map(stage => {
        const stageApps = apps.filter(a => a.status === stage.id);
        return `
          <div class="kanban-column" data-stage="${stage.id}">
            <div class="column-header">
              <span>${stage.label}</span>
              <span class="column-count">${stageApps.length}</span>
            </div>
            <div class="kanban-cards" id="column-${stage.id}">
              ${stageApps.map(app => renderKanbanCard(app)).join('')}
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;

  // Attach Drag & Drop handlers
  setupDragAndDrop(container);
}

function renderKanbanCard(app) {
  const score = app.overall_score || 0;
  let scoreColor = '#ef4444';
  if (score >= 81) scoreColor = '#c084fc';
  else if (score >= 61) scoreColor = '#34d399';
  else if (score >= 31) scoreColor = '#fbbf24';

  return `
    <div class="kanban-card" draggable="true" data-app-id="${app.id}">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;">
        <div style="font-weight: 700; font-size: 0.9rem; color: #fff;">${escapeHtml(app.company)}</div>
        <span style="font-size: 0.75rem; font-weight: 800; font-family: var(--font-mono); color: ${scoreColor}; background: rgba(0,0,0,0.3); padding: 0.15rem 0.4rem; border-radius: 4px;">
          ${score}
        </span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">${escapeHtml(app.title)}</div>
      <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
        <span>📍 ${escapeHtml(app.location || 'N/A')}</span>
        ${app.apply_url ? `<a href="${escapeHtml(app.apply_url)}" target="_blank" style="color: var(--accent-cyan); text-decoration: none;">Link ↗</a>` : ''}
      </div>
    </div>
  `;
}

function setupDragAndDrop(container) {
  let draggedCard = null;

  container.querySelectorAll('.kanban-card').forEach(card => {
    card.addEventListener('dragstart', (e) => {
      draggedCard = card;
      card.style.opacity = '0.5';
      e.dataTransfer.setData('text/plain', card.getAttribute('data-app-id'));
    });

    card.addEventListener('dragend', () => {
      if (draggedCard) draggedCard.style.opacity = '1';
      draggedCard = null;
    });
  });

  container.querySelectorAll('.kanban-column').forEach(column => {
    column.addEventListener('dragover', (e) => {
      e.preventDefault();
      column.style.background = 'rgba(99, 102, 241, 0.1)';
    });

    column.addEventListener('dragleave', () => {
      column.style.background = '';
    });

    column.addEventListener('drop', async (e) => {
      e.preventDefault();
      column.style.background = '';
      const appId = e.dataTransfer.getData('text/plain');
      const newStage = column.getAttribute('data-stage');

      if (appId && newStage) {
        await API.updateApplication(appId, { status: newStage });
        renderTrackerView(container); // Refresh board
      }
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
