/**
 * Employmentmaxxing Profile Component — NERV Sci-Fi Telemetry Command HUD
 * Integrates Hero Candidate Header, NERV Emblem, Categorized Skills, Projects, and PDF Viewer.
 */

import { API } from '../utils/api.js';

export async function renderProfileView(container) {
  const profile = await API.getProfile();
  let currentSkills = [...(profile.skills || [])];
  let projects = profile.projects || [
    {
      name: "DocWeave",
      description: "Distributed Go crawler with PostgreSQL SKIP LOCKED leases processing 1,000 pages at 10 pages/sec with Prometheus/Grafana.",
      tech_stack: ["Go", "PostgreSQL", "Docker", "Prometheus", "Grafana", "REST APIs"]
    },
    {
      name: "Devflow Agent",
      description: "Agentic developer tooling platform automating issue planning and workflow execution with FastAPI, PostgreSQL, Redis, Docker, GitHub Actions, React.",
      tech_stack: ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "GitHub Actions", "React"]
    },
    {
      name: "Odysseus AI Workspace",
      description: "Open source contributor to 73k+ star self-hosted AI workspace (fixed multi-line prompt & markdown search bug).",
      tech_stack: ["Python", "Docker", "Linux", "LLMs"]
    },
    {
      name: "Barter",
      description: "Full-stack skill exchange platform with React, TypeScript, Flask, Firebase, WebSockets, OpenAI API, and AR navigation.",
      tech_stack: ["React", "TypeScript", "Flask", "Firebase", "OpenAI API", "WebSockets"]
    },
    {
      name: "FableFrog",
      description: "Storyteller Speech-to-Speech AI chatbot using Python, React Native, OpenAI, Hugging Face, ElevenLabs, RAG, and PEFT fine-tuning.",
      tech_stack: ["Python", "React Native", "OpenAI API", "Hugging Face", "RAG", "ElevenLabs"]
    }
  ];

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto;" class="animate-fade-up">
      
      <!-- NERV Cyber-Telemetry Candidate Hero Header -->
      <div class="profile-hero-card">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1.25rem;">
          
          <div class="profile-avatar-container">
            <div style="position: relative;">
              <img src="/static/nerv_logo.png" alt="NERV Emblem" class="profile-avatar" style="object-fit: contain; padding: 4px; background: #000; border-color: #ff2a2a; box-shadow: 0 0 15px rgba(255, 42, 42, 0.5);">
            </div>
            <div class="profile-hero-info">
              <div style="display: flex; align-items: center; gap: 0.6rem;">
                <h1>${escapeHtml(profile.name || 'Keshav Jindal')}</h1>
                <span style="font-family: var(--font-mono); font-size: 0.7rem; color: #ff2a2a; background: rgba(255, 42, 42, 0.1); border: 1px solid rgba(255, 42, 42, 0.4); padding: 2px 6px; border-radius: 3px;">NERV OPERATIONAL</span>
              </div>
              <p style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-secondary);">
                ${escapeHtml(profile.degree || 'BS Computer Science')} @ ${escapeHtml(profile.university || 'California State University Long Beach')} ('${profile.graduation_year || 2027})
              </p>
              <p style="font-family: var(--font-mono); font-size: 0.72rem; color: #ff4d4d; font-style: italic; margin-top: 0.25rem;">
                "GOD'S IN HIS HEAVEN. ALL'S RIGHT WITH THE WORLD."
              </p>
              
              <div class="profile-hero-pills">
                <span class="profile-pill highlight">● NERV TELEMETRY ACTIVE</span>
                <span class="profile-pill">⚡ <span id="hero-skill-count">${currentSkills.length}</span> SKILLS INDEXED</span>
                <span class="profile-pill">🎯 TARGET: AI/ML · SWE · QUANTUM</span>
                <span class="profile-pill">📍 CALIFORNIA / US REMOTE</span>
              </div>
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem; min-width: 180px;">
            <a href="/static/Keshav_Jindal.pdf" target="_blank" class="btn-primary" style="text-decoration: none; text-align: center; font-size: 0.8rem; padding: 0.55rem 1rem;">
              ↗ Open Resume PDF
            </a>
            <a href="/static/Keshav_Jindal.pdf" download="Keshav_Jindal.pdf" class="btn-secondary" style="text-decoration: none; text-align: center; font-size: 0.8rem; padding: 0.55rem 1rem;">
              📥 Download PDF
            </a>
          </div>

        </div>
      </div>

      <!-- Dock Navigation Tabs -->
      <div class="sub-tabs-nav">
        <button class="sub-tab-btn active" id="sub-tab-matrix">⚡ SKILL MATRIX DOCK</button>
        <button class="sub-tab-btn" id="sub-tab-projects">🚀 MISSION PROJECTS (${projects.length})</button>
        <button class="sub-tab-btn" id="sub-tab-resume">📄 RESUME PDF PREVIEW (Keshav_Jindal.pdf)</button>
        <button class="sub-tab-btn" id="sub-tab-settings">⚙️ CANDIDATE SETTINGS</button>
      </div>

      <!-- View 1: Skill Matrix -->
      <div id="sub-view-matrix">
        <div style="background: var(--bg-card); border: 1px solid var(--border-purple); padding: 1.5rem; margin-bottom: 2rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem;">
            <h3 style="font-size: 1rem; font-family: var(--font-mono); font-weight: 800; color: var(--accent-green);">
              ⚡ TECHNICAL SKILLS MATRIX (<span id="skill-matrix-count">${currentSkills.length}</span> SKILLS LOADED)
            </h3>
            <div style="display: flex; gap: 0.5rem; width: 320px;">
              <input type="text" class="form-input" id="new-skill-input" placeholder="Add skill (e.g. PyTorch, CUDA)..." style="font-size: 0.8rem; background: #000; border-color: var(--border-purple);">
              <button type="button" class="btn-secondary" id="btn-add-skill" style="padding: 0.4rem 0.8rem; font-size: 0.75rem;">+ Add</button>
            </div>
          </div>

          <!-- Skills Matrix Container -->
          <div id="skills-matrix-container"></div>
        </div>
      </div>

      <!-- View 2: Featured Projects Showcase -->
      <div id="sub-view-projects" style="display: none;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-purple); padding: 1.5rem; margin-bottom: 2rem;">
          <h3 style="font-size: 1rem; font-family: var(--font-mono); font-weight: 800; color: var(--accent-green); margin-bottom: 1.25rem;">
            🚀 FEATURED ENGINEERING PROJECTS & CONTRIBUTIONS
          </h3>
          
          <div class="projects-grid">
            ${projects.map((proj) => `
              <div class="project-card">
                <div class="project-title">
                  <span>${escapeHtml(proj.name)}</span>
                  <span style="font-size: 0.65rem; color: var(--accent-purple); font-weight: 700;">VERIFIED</span>
                </div>
                <div class="project-desc">${escapeHtml(proj.description)}</div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.3rem;">
                  ${(proj.tech_stack || []).map(t => `<span class="profile-pill" style="font-size: 0.65rem; padding: 0.15rem 0.4rem;">${escapeHtml(t)}</span>`).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- View 3: Resume PDF Preview -->
      <div id="sub-view-resume" style="display: none;">
        <div class="resume-preview-card">
          <div class="resume-toolbar">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
              <img src="/static/nerv_logo.png" alt="NERV Emblem" style="height: 18px; width: 18px; object-fit: contain;">
              <span style="color: var(--accent-green);">● NERV RESUME DOCK INDEXED</span>
              <span style="color: var(--text-muted);">|</span>
              <span style="color: var(--accent-purple);">Keshav_Jindal.pdf</span>
            </div>
            <div class="resume-actions">
              <a href="/static/Keshav_Jindal.pdf" target="_blank" class="btn-secondary" style="text-decoration: none; padding: 0.4rem 0.8rem; font-size: 0.75rem;">
                ↗ Open Fullscreen
              </a>
              <a href="/static/Keshav_Jindal.pdf" download="Keshav_Jindal.pdf" class="btn-primary" style="text-decoration: none; padding: 0.4rem 0.8rem; font-size: 0.75rem;">
                📥 Download PDF
              </a>
            </div>
          </div>
          <object data="/static/Keshav_Jindal.pdf" type="application/pdf" class="pdf-object-container">
            <div style="padding: 2rem; text-align: center; color: var(--text-secondary);">
              <p>Your browser does not support embedded PDF viewing.</p>
              <p style="margin-top: 1rem;">
                <a href="/static/Keshav_Jindal.pdf" target="_blank" class="btn-primary" style="text-decoration: none;">
                  Click here to view Keshav_Jindal.pdf
                </a>
              </p>
            </div>
          </object>
        </div>
      </div>

      <!-- View 4: Candidate Settings & Profile Context -->
      <div id="sub-view-settings" style="display: none;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-purple); padding: 1.75rem; margin-bottom: 2rem;">
          <form id="profile-form">
            <div class="profile-grid">
              <div class="form-group">
                <label class="form-label">Full Name</label>
                <input type="text" class="form-input" id="prof-name" value="${escapeHtml(profile.name || 'Keshav Jindal')}">
              </div>
              <div class="form-group">
                <label class="form-label">University / Institution</label>
                <input type="text" class="form-input" id="prof-uni" value="${escapeHtml(profile.university || 'California State University Long Beach')}">
              </div>
              <div class="form-group">
                <label class="form-label">Degree & Major</label>
                <input type="text" class="form-input" id="prof-degree" value="${escapeHtml(profile.degree || 'BS Computer Science')}">
              </div>
              <div class="form-group">
                <label class="form-label">Expected Graduation Year</label>
                <input type="number" class="form-input" id="prof-grad-year" value="${profile.graduation_year || 2027}">
              </div>
            </div>

            <div class="form-group" style="margin-top: 1.25rem;">
              <label class="form-label">Additional Context & Differentiators</label>
              <textarea class="form-textarea" id="prof-context" rows="4" style="background:#000; border:1px solid var(--border-purple); font-family:var(--font-mono);">${escapeHtml(profile.additional_context || '')}</textarea>
            </div>

            <button type="submit" class="btn-primary" style="margin-top: 1.25rem; padding: 0.75rem 1.5rem; font-size: 0.95rem;">
              💾 Save Profile & Recalculate Scores
            </button>
          </form>
        </div>
      </div>

    </div>
  `;

  // Sub-tabs switching
  const tabMatrix = container.querySelector('#sub-tab-matrix');
  const tabProjects = container.querySelector('#sub-tab-projects');
  const tabResume = container.querySelector('#sub-tab-resume');
  const tabSettings = container.querySelector('#sub-tab-settings');

  const viewMatrix = container.querySelector('#sub-view-matrix');
  const viewProjects = container.querySelector('#sub-view-projects');
  const viewResume = container.querySelector('#sub-view-resume');
  const viewSettings = container.querySelector('#sub-view-settings');

  const allTabs = [tabMatrix, tabProjects, tabResume, tabSettings];
  const allViews = [viewMatrix, viewProjects, viewResume, viewSettings];

  const switchTab = (activeTab, activeView) => {
    allTabs.forEach(t => t && t.classList.remove('active'));
    allViews.forEach(v => v && (v.style.display = 'none'));
    if (activeTab) activeTab.classList.add('active');
    if (activeView) activeView.style.display = 'block';
  };

  tabMatrix.onclick = () => switchTab(tabMatrix, viewMatrix);
  tabProjects.onclick = () => switchTab(tabProjects, viewProjects);
  tabResume.onclick = () => switchTab(tabResume, viewResume);
  tabSettings.onclick = () => switchTab(tabSettings, viewSettings);

  // Categorize & Render Skills
  const renderCategorizedSkills = () => {
    const matrixBox = container.querySelector('#skills-matrix-container');
    const heroCount = container.querySelector('#hero-skill-count');
    const matrixCount = container.querySelector('#skill-matrix-count');

    if (heroCount) heroCount.textContent = currentSkills.length;
    if (matrixCount) matrixCount.textContent = currentSkills.length;

    // Grouping categories
    const categories = {
      "🧠 AI, Deep Learning & LLMs": ["Python", "PyTorch", "TensorFlow", "scikit-learn", "OpenCV", "NumPy", "Pandas", "LLMs", "RAG", "Vector DBs", "Prompt Engineering", "Fine-tuning", "Computer Vision", "Multi-Agent Systems", "Time-Series Analysis"],
      "⚙️ Core Backend & Systems": ["C++", "Go", "Rust", "Java", "C", "SQL", "FastAPI", "Flask", "Node.js", "PostgreSQL", "Redis", "REST APIs", "gRPC"],
      "🌐 Frontend & Mobile": ["TypeScript", "JavaScript", "React", "Next.js", "React Native", "HTML", "CSS"],
      "☁️ Cloud, Infra & DevOps": ["Docker", "AWS", "Firebase", "Git", "GitHub Actions", "Terraform", "CI/CD", "Linux"]
    };

    let allocatedSkills = new Set();
    let categoryHTML = '';

    for (const [catName, catSkills] of Object.entries(categories)) {
      const present = currentSkills.filter(s => catSkills.some(cs => cs.toLowerCase() === s.toLowerCase()));
      present.forEach(s => allocatedSkills.add(s.toLowerCase()));

      if (present.length > 0) {
        categoryHTML += `
          <div class="skill-category-block">
            <div class="skill-category-title">
              <span>${catName}</span>
              <span style="font-size: 0.7rem; color: var(--accent-green);">${present.length} SKILLS</span>
            </div>
            <div class="chip-matrix">
              ${present.map(skill => `
                <span class="skill-chip">
                  ${escapeHtml(skill)}
                  <span class="remove-btn" data-skill="${escapeHtml(skill)}">✕</span>
                </span>
              `).join('')}
            </div>
          </div>
        `;
      }
    }

    // Other/Custom skills
    const unallocated = currentSkills.filter(s => !allocatedSkills.has(s.toLowerCase()));
    if (unallocated.length > 0) {
      categoryHTML += `
        <div class="skill-category-block">
          <div class="skill-category-title">
            <span>✨ Additional Specialized Skills</span>
            <span style="font-size: 0.7rem; color: var(--accent-purple);">${unallocated.length} SKILLS</span>
          </div>
          <div class="chip-matrix">
            ${unallocated.map(skill => `
              <span class="skill-chip">
                ${escapeHtml(skill)}
                <span class="remove-btn" data-skill="${escapeHtml(skill)}">✕</span>
              </span>
            `).join('')}
          </div>
        </div>
      `;
    }

    matrixBox.innerHTML = categoryHTML;

    // Remove skill handler
    matrixBox.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const skillToRemove = e.target.getAttribute('data-skill');
        currentSkills = currentSkills.filter(s => s !== skillToRemove);
        renderCategorizedSkills();
      });
    });
  };

  renderCategorizedSkills();

  // Add skill handler
  const addSkill = () => {
    const input = container.querySelector('#new-skill-input');
    const val = input.value.trim();
    if (val && !currentSkills.some(s => s.toLowerCase() === val.toLowerCase())) {
      currentSkills.push(val);
      input.value = '';
      renderCategorizedSkills();
    }
  };

  container.querySelector('#btn-add-skill').onclick = addSkill;
  container.querySelector('#new-skill-input').onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill();
    }
  };

  // Form submit handler
  const form = container.querySelector('#profile-form');
  if (form) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const updated = {
        name: container.querySelector('#prof-name').value,
        university: container.querySelector('#prof-uni').value,
        degree: container.querySelector('#prof-degree').value,
        graduation_year: parseInt(container.querySelector('#prof-grad-year').value) || 2027,
        skills: currentSkills,
        additional_context: container.querySelector('#prof-context').value,
        projects: projects,
        preferred_locations: profile.preferred_locations || ["California", "United States", "Remote"],
        open_to_remote: true,
        target_roles: profile.target_roles || ["AI/ML", "SWE", "Quantum"],
      };

      await API.saveProfile(updated);
      alert('✅ Profile saved! Job chance scores are being recalculated in the background.');
    };
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
