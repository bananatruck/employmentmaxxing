/**
 * Employmentmaxxing API Client Wrapper
 */
const API_BASE = '/api';

export const API = {
  // Jobs
  async getJobs(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== null && val !== undefined && val !== '') {
        query.append(key, val);
      }
    });
    const res = await fetch(`${API_BASE}/jobs?${query.toString()}`);
    return res.json();
  },

  async getJobDetail(jobId) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    return res.json();
  },

  // Profile
  async getProfile() {
    const res = await fetch(`${API_BASE}/profile`);
    return res.json();
  },

  async saveProfile(profileData) {
    const res = await fetch(`${API_BASE}/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    return res.json();
  },

  // Applications
  async getApplications(status = null) {
    const url = status ? `${API_BASE}/applications?status=${status}` : `${API_BASE}/applications`;
    const res = await fetch(url);
    return res.json();
  },

  async createApplication(jobId, status = 'interested', notes = '') {
    const res = await fetch(`${API_BASE}/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, status, notes }),
    });
    return res.json();
  },

  async updateApplication(appId, updates) {
    const res = await fetch(`${API_BASE}/applications/${appId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return res.json();
  },

  async deleteApplication(appId) {
    const res = await fetch(`${API_BASE}/applications/${appId}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  // Analytics & Scrape
  async getAnalytics() {
    const res = await fetch(`${API_BASE}/analytics`);
    return res.json();
  },

  async getScrapeStatus() {
    const res = await fetch(`${API_BASE}/scrape/status`);
    return res.json();
  },

  async triggerScrape() {
    const res = await fetch(`${API_BASE}/scrape/trigger`, { method: 'POST' });
    return res.json();
  },
};
