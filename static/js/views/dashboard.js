/**
 * views/dashboard.js — Stats cards, funnel chart, recent activity, quick links.
 */

import { api } from "../api.js";
import { openPanel } from "./modal.js";
import { showToast, statusBadge, timeAgo } from "../app.js";

export async function renderDashboard() {
  const view = document.getElementById("view-dashboard");
  view.innerHTML = `
    <div class="view-header">
      <div class="view-title">Dashboard</div>
      <div class="view-subtitle">Your job search at a glance</div>
    </div>
    <div class="stats-grid" id="stats-grid">
      ${[1,2,3,4,5].map(() => `<div class="stat-card"><div class="skeleton" style="height:12px;width:60%;margin-bottom:10px"></div><div class="skeleton" style="height:36px;width:40%"></div></div>`).join("")}
    </div>
    <div class="dashboard-grid">
      <div>
        <div class="card" id="funnel-card">
          <div class="funnel-title">Application Pipeline</div>
          <div id="funnel-body"><div class="spinner" style="margin:20px auto"></div></div>
        </div>
        <div class="card" style="margin-top:16px">
          <div class="funnel-title">Quick Search Links</div>
          <div id="quick-links-body"><div class="spinner" style="margin:12px auto"></div></div>
        </div>
      </div>
      <div>
        <div class="card" id="activity-card" style="height:100%">
          <div class="funnel-title">Recent Activity</div>
          <div id="activity-body"><div class="spinner" style="margin:20px auto"></div></div>
        </div>
      </div>
    </div>
  `;

  try {
    const [stats, apps, cfg] = await Promise.all([
      api.getStats(),
      api.getApplications(),
      api.getConfig(),
    ]);
    _renderStats(stats);
    _renderFunnel(stats);
    _renderActivity(apps);
    _renderQuickLinks(cfg.target_roles);
  } catch (err) {
    showToast("Failed to load dashboard: " + err.message, "error");
  }
}

function _renderStats(s) {
  const applied    = s.applied    || 0;
  const rejected   = s.rejected   || 0;
  const responded  = applied + rejected;
  const responseRate = responded > 0 ? Math.round((applied / responded) * 100) : 0;

  document.getElementById("stats-grid").innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Total Found</div>
      <div class="stat-value">${s.total_jobs_found || 0}</div>
    </div>
    <div class="stat-card accent-blue">
      <div class="stat-label">Applied</div>
      <div class="stat-value">${applied}</div>
    </div>
    <div class="stat-card accent-green">
      <div class="stat-label">Interviews</div>
      <div class="stat-value">${s.interview || 0}</div>
    </div>
    <div class="stat-card ${(s.offer || 0) > 0 ? "accent-green" : ""}">
      <div class="stat-label">Offers</div>
      <div class="stat-value">${s.offer || 0}${(s.offer || 0) > 0 ? " 🎉" : ""}</div>
    </div>
    <div class="stat-card accent-purple">
      <div class="stat-label">Response Rate</div>
      <div class="stat-value">${responseRate}%</div>
    </div>
  `;
}

function _renderFunnel(s) {
  const stages = [
    { key: "saved",       label: "Saved",        color: "var(--status-saved)" },
    { key: "applied",     label: "Applied",       color: "var(--status-applied)" },
    { key: "followed_up", label: "Followed Up",   color: "var(--status-followed_up)" },
    { key: "interview",   label: "Interview",     color: "var(--status-interview)" },
    { key: "offer",       label: "Offer",         color: "var(--status-offer)" },
  ];

  // Add unsaved jobs to "saved" count (total minus those with any status)
  const totalTracked = stages.reduce((sum, st) => sum + (s[st.key] || 0), 0);
  const maxCount     = Math.max(1, (s.total_jobs_found || 0));

  document.getElementById("funnel-body").innerHTML = stages.map((stage, i) => {
    const count = s[stage.key] || 0;
    const pct   = Math.max(4, Math.round((count / maxCount) * 100));
    const prev  = i > 0 ? (s[stages[i - 1].key] || 0) : null;
    const conv  = (prev !== null && prev > 0) ? Math.round((count / prev) * 100) + "%" : "";
    return `
      <div class="funnel-row">
        <div class="funnel-label">${stage.label}</div>
        <div class="funnel-bar-wrap">
          <div class="funnel-bar" style="background:${stage.color};width:${pct}%">${count > 0 ? count : ""}</div>
        </div>
        <div class="funnel-count">${count}</div>
        <div class="funnel-pct">${conv}</div>
      </div>`;
  }).join("");
}

function _renderActivity(apps) {
  const recent = apps.slice(0, 10);
  if (recent.length === 0) {
    document.getElementById("activity-body").innerHTML = `
      <div class="empty-state">
        <p>No tracked applications yet.<br>Go to All Jobs and click <strong>Apply</strong> to start.</p>
        <a href="#jobs" class="btn btn-ghost btn-sm">Browse Jobs →</a>
      </div>`;
    return;
  }

  document.getElementById("activity-body").innerHTML = `
    <div class="activity-list">
      ${recent.map(app => `
        <div class="activity-item" data-id="${app.id}">
          <div class="activity-info">
            <div class="activity-title">${_esc(app.title)}</div>
            <div class="activity-company">${_esc(app.company)}</div>
          </div>
          <div class="activity-meta">
            ${statusBadge(app.status)}
            <span class="activity-time">${timeAgo(app.updated_at)}</span>
          </div>
        </div>
      `).join("")}
    </div>`;

  document.querySelectorAll(".activity-item").forEach(el => {
    el.addEventListener("click", () => openPanel(parseInt(el.dataset.id)));
  });
}

function _renderQuickLinks(roles) {
  // Common job board URL patterns
  const boards = [
    { label: "LinkedIn",  url: r => `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(r)}&location=United+States`, icon: "🔗" },
    { label: "Indeed",    url: r => `https://www.indeed.com/jobs?q=${encodeURIComponent(r)}&l=Remote`, icon: "🔍" },
    { label: "Glassdoor", url: r => `https://www.glassdoor.com/Job/jobs.htm?suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword=${encodeURIComponent(r)}`, icon: "🪟" },
    { label: "Dribbble",  url: r => `https://dribbble.com/jobs?location=Anywhere&keywords=${encodeURIComponent(r)}`, icon: "🏀" },
    { label: "Wellfound", url: r => `https://wellfound.com/jobs?q=${encodeURIComponent(r)}`, icon: "🚀" },
    { label: "Built In",  url: r => `https://builtin.com/jobs?search=${encodeURIComponent(r)}`, icon: "🏗️" },
  ];

  const role = roles?.[0] || "UX Designer";

  document.getElementById("quick-links-body").innerHTML = `
    <div class="quick-links">
      ${boards.map(b => `
        <a href="${b.url(role)}" target="_blank" rel="noopener" class="quick-link-btn">
          ${b.icon} ${b.label}
        </a>
      `).join("")}
    </div>
    <div style="margin-top:10px;font-size:12px;color:var(--color-text-faint)">Showing links for: <em>${_esc(role)}</em></div>
  `;
}

function _esc(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
