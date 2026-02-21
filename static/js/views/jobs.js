/**
 * views/jobs.js — All Jobs table view with filters + quick-action buttons.
 */

import { api } from "../api.js";
import { openPanel } from "./modal.js";
import { showToast, scoreClass, statusBadge, timeAgo } from "../app.js";

const PAGE_SIZE = 75;

// View state
let _jobs       = [];
let _displayed  = PAGE_SIZE;
let _sortCol    = "score";
let _sortAsc    = false;
let _filters    = { q: "", status: "", source: "", min_score: 0, is_remote: "" };

export async function renderJobs() {
  const view = document.getElementById("view-jobs");
  view.innerHTML = `
    <div class="view-header">
      <div class="view-title">All Jobs</div>
      <div class="view-subtitle">Browse and manage all saved job listings</div>
    </div>

    <div class="toolbar">
      <div class="search-input-wrap">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input type="text" id="jobs-search" class="search-input" placeholder="Search title, company, description…" value="${_filters.q}">
      </div>
      <div class="toolbar-sep"></div>
      <div class="toolbar-group">
        <select id="filter-status" class="filter-select">
          <option value="">All statuses</option>
          <option value="saved">Saved</option>
          <option value="applied">Applied</option>
          <option value="followed_up">Followed Up</option>
          <option value="interview">Interview</option>
          <option value="offer">Offer</option>
          <option value="rejected">Rejected</option>
          <option value="declined">Declined</option>
          <option value="withdrawn">Withdrawn</option>
        </select>
        <select id="filter-source" class="filter-select">
          <option value="">All sources</option>
        </select>
        <label class="toggle-remote">
          <input type="checkbox" id="filter-remote" ${_filters.is_remote === "1" ? "checked" : ""}>
          Remote only
        </label>
        <select id="filter-sort" class="filter-select">
          <option value="score" ${_sortCol === "score" ? "selected" : ""}>Sort: Best match</option>
          <option value="date"  ${_sortCol === "date"  ? "selected" : ""}>Sort: Newest</option>
          <option value="company" ${_sortCol === "company" ? "selected" : ""}>Sort: Company A–Z</option>
        </select>
      </div>
    </div>

    <div class="table-wrap">
      <table id="jobs-table">
        <thead>
          <tr>
            <th style="width:42px">Score</th>
            <th>Title / Company</th>
            <th>Location</th>
            <th>Salary</th>
            <th>Posted</th>
            <th>Status</th>
            <th style="min-width:200px">Actions</th>
          </tr>
        </thead>
        <tbody id="jobs-tbody">
          <tr><td colspan="7"><div class="empty-state"><div class="spinner" style="margin:0 auto 12px"></div><p>Loading jobs…</p></div></td></tr>
        </tbody>
      </table>
      <div class="table-footer" id="table-footer" style="display:none">
        <span id="table-count" class="muted text-sm"></span>
        <button id="load-more-btn" class="load-more-btn hidden">Load more</button>
      </div>
    </div>
  `;

  // Restore filter select values
  document.getElementById("filter-status").value = _filters.status;
  document.getElementById("filter-sort").value   = _sortCol;

  // Wire controls
  let debounceTimer;
  document.getElementById("jobs-search").addEventListener("input", e => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { _filters.q = e.target.value.trim(); _displayed = PAGE_SIZE; _loadJobs(); }, 300);
  });
  document.getElementById("filter-status").addEventListener("change", e => { _filters.status = e.target.value; _displayed = PAGE_SIZE; _loadJobs(); });
  document.getElementById("filter-remote").addEventListener("change", e => { _filters.is_remote = e.target.checked ? "1" : ""; _displayed = PAGE_SIZE; _loadJobs(); });
  document.getElementById("filter-sort").addEventListener("change", e => { _sortCol = e.target.value; _displayed = PAGE_SIZE; _loadJobs(); });
  document.getElementById("load-more-btn").addEventListener("click", () => { _displayed += PAGE_SIZE; _renderTable(); });

  // Populate source filter from config, then load
  try {
    const cfg = await api.getConfig();
    const sel = document.getElementById("filter-source");
    cfg.sources.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s; opt.textContent = s;
      if (s === _filters.source) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", e => { _filters.source = e.target.value; _displayed = PAGE_SIZE; _loadJobs(); });
  } catch (_) {}

  await _loadJobs();
}

async function _loadJobs() {
  const params = {
    q:         _filters.q,
    status:    _filters.status,
    source:    _filters.source,
    min_score: _filters.min_score,
    is_remote: _filters.is_remote,
    sort:      _sortCol,
    limit:     500,
  };

  try {
    _jobs = await api.getJobs(params);
    // Update sidebar count badge
    const badge = document.getElementById("jobs-count-badge");
    if (badge) badge.textContent = _jobs.length;
  } catch (err) {
    showToast("Failed to load jobs: " + err.message, "error");
    return;
  }

  _displayed = PAGE_SIZE;
  _renderTable();
}

function _renderTable() {
  const tbody  = document.getElementById("jobs-tbody");
  const footer = document.getElementById("table-footer");
  const count  = document.getElementById("table-count");
  const more   = document.getElementById("load-more-btn");

  if (!tbody) return;

  const slice = _jobs.slice(0, _displayed);

  if (_jobs.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="7">
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <h3>No jobs found</h3>
          <p>Try adjusting your filters or run a new search from the sidebar.</p>
        </div>
      </td></tr>`;
    if (footer) footer.style.display = "none";
    return;
  }

  tbody.innerHTML = slice.map(job => _jobRow(job)).join("");

  if (footer) footer.style.display = "flex";
  if (count)  count.textContent = `Showing ${slice.length} of ${_jobs.length} jobs`;
  if (more) {
    if (_displayed < _jobs.length) {
      more.classList.remove("hidden");
      more.textContent = `Load ${Math.min(PAGE_SIZE, _jobs.length - _displayed)} more`;
    } else {
      more.classList.add("hidden");
    }
  }

  // Bind row + action button events
  tbody.querySelectorAll("tr[data-id]").forEach(row => {
    // Click row body (not action buttons) to open panel
    row.addEventListener("click", e => {
      if (e.target.closest(".action-btns")) return;
      openPanel(parseInt(row.dataset.id));
    });
  });

  tbody.querySelectorAll(".btn-quick-action").forEach(btn => {
    btn.addEventListener("click", async e => {
      e.stopPropagation();
      const jobId  = parseInt(btn.closest("tr").dataset.id);
      const status = btn.dataset.status;
      await _quickAction(jobId, status);
    });
  });
}

function _jobRow(job) {
  const jobId   = job.id;
  const status  = job.app_status || "saved";
  const score   = job.score || 0;
  const remote  = job.is_remote;
  const loc     = remote
    ? `<span class="tag-remote">Remote</span>`
    : (job.location ? `<span class="muted text-sm">${_esc(job.location)}</span>` : `<span class="muted text-sm">—</span>`);
  const salary  = job.salary ? `<span class="text-sm">${_esc(job.salary)}</span>` : `<span class="muted text-sm">—</span>`;
  const posted  = job.date_posted ? `<span class="text-sm muted">${timeAgo(job.date_posted)}</span>` : `<span class="muted text-sm">—</span>`;

  return `
    <tr data-id="${jobId}">
      <td><span class="score-dot ${scoreClass(score)}">${score}</span></td>
      <td class="col-title">
        <span class="job-title">${_esc(job.title)}</span>
        <span class="job-company">${_esc(job.company)}</span>
      </td>
      <td>${loc}</td>
      <td>${salary}</td>
      <td>${posted}</td>
      <td>${statusBadge(status)}</td>
      <td class="col-actions">
        <div class="action-btns">
          ${_actionButtons(status, jobId)}
        </div>
      </td>
    </tr>`;
}

function _actionButtons(status, jobId) {
  const btns = _nextStatuses(status);
  return btns.map(([label, s, cls]) =>
    `<button class="btn btn-xs btn-quick-action ${cls}" data-status="${s}" title="Mark as ${s}">${label}</button>`
  ).join("");
}

function _nextStatuses(current) {
  // Returns [label, status, css-class] tuples
  switch (current) {
    case "saved":
      return [["Apply", "applied", "btn-action-apply"], ["Skip", "declined", "btn-action-skip"]];
    case "applied":
      return [["Follow Up", "followed_up", "btn-action-followup"], ["Interview", "interview", "btn-action-interview"], ["Reject", "rejected", "btn-action-reject"]];
    case "followed_up":
      return [["Interview", "interview", "btn-action-interview"], ["Reject", "rejected", "btn-action-reject"]];
    case "interview":
      return [["Offer!", "offer", "btn-action-offer"], ["Reject", "rejected", "btn-action-reject"]];
    case "offer":
      return [["Declined", "declined", "btn-action-skip"]];
    default:
      return [["Reopen", "saved", "btn-action-skip"]];
  }
}

async function _quickAction(jobId, status) {
  try {
    const res = await api.setStatus(jobId, status);
    // Update the job in our local array
    const idx = _jobs.findIndex(j => j.id === jobId);
    if (idx !== -1) _jobs[idx] = res.job;

    // Update just this row in the DOM
    const row = document.querySelector(`tr[data-id="${jobId}"]`);
    if (row) {
      row.outerHTML = _jobRow(res.job);
      // Re-bind new row
      const newRow = document.querySelector(`tr[data-id="${jobId}"]`);
      if (newRow) {
        newRow.addEventListener("click", e => {
          if (e.target.closest(".action-btns")) return;
          openPanel(parseInt(newRow.dataset.id));
        });
        newRow.querySelectorAll(".btn-quick-action").forEach(btn => {
          btn.addEventListener("click", async e => {
            e.stopPropagation();
            await _quickAction(parseInt(btn.closest("tr").dataset.id), btn.dataset.status);
          });
        });
        // Brief highlight
        newRow.classList.add("row-highlight");
        setTimeout(() => newRow.classList.remove("row-highlight"), 800);
      }
    }

    const labels = { applied: "Marked as Applied", followed_up: "Followed Up!", interview: "Interview noted", offer: "Offer logged!", rejected: "Marked Rejected", declined: "Skipped", saved: "Restored to saved" };
    showToast(labels[status] || `Status: ${status}`, "success");
  } catch (err) {
    showToast("Update failed: " + err.message, "error");
  }
}

/** Refresh a single row after panel status change */
export async function refreshJobRow(jobId) {
  const idx = _jobs.findIndex(j => j.id === jobId);
  if (idx === -1) return;
  try {
    const job = await api.getJob(jobId);
    _jobs[idx] = job;
    const row = document.querySelector(`tr[data-id="${jobId}"]`);
    if (row) {
      row.outerHTML = _jobRow(job);
      const newRow = document.querySelector(`tr[data-id="${jobId}"]`);
      if (newRow) {
        newRow.addEventListener("click", e => {
          if (e.target.closest(".action-btns")) return;
          openPanel(parseInt(newRow.dataset.id));
        });
        newRow.querySelectorAll(".btn-quick-action").forEach(btn => {
          btn.addEventListener("click", async e => {
            e.stopPropagation();
            await _quickAction(parseInt(btn.closest("tr").dataset.id), btn.dataset.status);
          });
        });
      }
    }
  } catch (_) {}
}

function _esc(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
