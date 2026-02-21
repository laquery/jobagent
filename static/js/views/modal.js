/**
 * views/modal.js — Job detail slide-over panel.
 */

import { api } from "../api.js";
import { showToast, statusBadge, scoreClass, timeAgo } from "../app.js";
import { refreshJobRow } from "./jobs.js";

let _currentJobId = null;

export async function openPanel(jobId) {
  _currentJobId = jobId;
  const panel   = document.getElementById("detail-panel");
  const overlay = document.getElementById("overlay");
  const content = document.getElementById("panel-content");

  // Show panel immediately with loading state
  panel.classList.remove("hidden");
  overlay.classList.remove("hidden");
  requestAnimationFrame(() => {
    panel.classList.add("visible");
    overlay.classList.add("visible");
  });

  content.innerHTML = `<div style="padding:40px;text-align:center"><div class="spinner" style="margin:0 auto"></div></div>`;

  try {
    const job = await api.getJob(jobId);
    _renderPanel(job);
  } catch (err) {
    content.innerHTML = `<div style="padding:32px;text-align:center;color:var(--color-text-muted)">Failed to load job: ${err.message}</div>`;
  }
}

export function closePanel() {
  const panel   = document.getElementById("detail-panel");
  const overlay = document.getElementById("overlay");
  panel.classList.remove("visible");
  overlay.classList.remove("visible");
  setTimeout(() => {
    panel.classList.add("hidden");
    overlay.classList.add("hidden");
  }, 290);
  _currentJobId = null;
}

function _renderPanel(job) {
  const content = document.getElementById("panel-content");
  const status  = job.app_status || "saved";
  const remote  = job.is_remote;

  const tags = [
    remote ? `<span class="tag-remote">Remote</span>` : "",
    job.employment_type ? `<span class="tag-source">${_esc(_formatEmpType(job.employment_type))}</span>` : "",
    job.experience_level ? `<span class="tag-source">${_esc(job.experience_level)}</span>` : "",
    `<span class="score-dot ${scoreClass(job.score || 0)}" style="font-size:12px">${job.score || 0} score</span>`,
  ].filter(Boolean).join("");

  content.innerHTML = `
    <div class="panel-header">
      <button class="panel-close" id="panel-close-btn" title="Close (Esc)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
      <div class="panel-title">${_esc(job.title)}</div>
      <div class="panel-company">${_esc(job.company)}${job.location ? " · " + _esc(job.location) : ""}</div>
      <div class="panel-tags">${tags}</div>
      <div class="panel-actions">
        ${job.url ? `<a href="${_esc(job.url)}" target="_blank" rel="noopener" class="btn btn-primary btn-sm">Apply Now ↗</a>` : ""}
        <select id="panel-status-sel" class="panel-status-select">
          ${["saved","applied","followed_up","interview","offer","rejected","declined","withdrawn"].map(s =>
            `<option value="${s}" ${s === status ? "selected" : ""}>${_statusLabel(s)}</option>`
          ).join("")}
        </select>
      </div>
    </div>

    ${_timelineSection(job)}

    <div class="panel-section">
      <div class="panel-section-title">Details</div>
      <div class="details-grid">
        <div class="detail-item">
          <div class="detail-item-label">Salary</div>
          <div class="detail-item-value">${_esc(job.salary || "—")}</div>
        </div>
        <div class="detail-item">
          <div class="detail-item-label">Date Posted</div>
          <div class="detail-item-value">${job.date_posted ? _esc(job.date_posted) : "—"}</div>
        </div>
        <div class="detail-item">
          <div class="detail-item-label">Apply Deadline</div>
          <div class="detail-item-value">${job.apply_deadline ? `<strong style="color:#d97706">${_esc(job.apply_deadline)}</strong>` : "—"}</div>
        </div>
        <div class="detail-item">
          <div class="detail-item-label">Source</div>
          <div class="detail-item-value">${_esc(job.source || "—")}</div>
        </div>
        <div class="detail-item">
          <div class="detail-item-label">Experience</div>
          <div class="detail-item-value">${_esc(job.experience_level || "—")}</div>
        </div>
        <div class="detail-item">
          <div class="detail-item-label">Employment</div>
          <div class="detail-item-value">${_esc(_formatEmpType(job.employment_type) || "—")}</div>
        </div>
      </div>
    </div>

    <div class="panel-section">
      <div class="panel-section-title">Notes</div>
      <textarea id="panel-notes" class="notes-textarea" placeholder="Add private notes about this application…">${_esc(job.app_notes || "")}</textarea>
      <div id="notes-hint" class="notes-save-hint">Saves automatically when you click away</div>
    </div>

    ${job.description ? `
    <div class="panel-section">
      <div class="panel-section-title">Job Description</div>
      <div class="description-text" id="panel-desc"></div>
    </div>` : ""}
  `;

  // Set description as textContent (safe, prevents XSS from scraped HTML)
  const descEl = document.getElementById("panel-desc");
  if (descEl) descEl.textContent = job.description || "";

  // Close button
  document.getElementById("panel-close-btn").addEventListener("click", closePanel);

  // Status change
  document.getElementById("panel-status-sel").addEventListener("change", async e => {
    const newStatus = e.target.value;
    const notes     = document.getElementById("panel-notes")?.value || "";
    try {
      await api.setStatus(job.id, newStatus, notes);
      job.app_status = newStatus;
      showToast(`Status updated to "${_statusLabel(newStatus)}"`, "success");
      refreshJobRow(job.id);
    } catch (err) {
      showToast("Failed to update status: " + err.message, "error");
      e.target.value = status; // revert
    }
  });

  // Notes auto-save on blur
  const notesEl = document.getElementById("panel-notes");
  if (notesEl) {
    notesEl.addEventListener("blur", async () => {
      const notes = notesEl.value;
      try {
        await api.updateNotes(job.id, notes);
        const hint = document.getElementById("notes-hint");
        if (hint) {
          hint.textContent = "Saved ✓";
          hint.classList.add("saved");
          setTimeout(() => {
            hint.textContent = "Saves automatically when you click away";
            hint.classList.remove("saved");
          }, 2000);
        }
        refreshJobRow(job.id);
      } catch (err) {
        showToast("Failed to save notes", "error");
      }
    });
  }
}

function _timelineSection(job) {
  const events = [];
  if (job.applied_at)   events.push({ label: "Applied",       date: job.applied_at,   color: "var(--status-applied)" });
  if (job.followed_up)  events.push({ label: "Followed Up",   date: job.followed_up,  color: "var(--status-followed_up)" });
  if (job.interview_at) events.push({ label: "Interview",     date: job.interview_at, color: "var(--status-interview)" });

  if (events.length === 0) return "";

  return `
    <div class="panel-section">
      <div class="panel-section-title">Timeline</div>
      <div class="timeline">
        ${events.map(ev => `
          <div class="timeline-item">
            <div class="timeline-dot" style="background:${ev.color}"></div>
            <div class="timeline-info">
              <div class="timeline-label">${ev.label}</div>
              <div class="timeline-date">${ev.date.slice(0, 10)} · ${timeAgo(ev.date)}</div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>`;
}

function _statusLabel(s) {
  return { saved: "Saved", applied: "Applied", followed_up: "Followed Up", interview: "Interview", offer: "Offer", rejected: "Rejected", declined: "Declined", withdrawn: "Withdrawn" }[s] || s;
}

function _formatEmpType(t) {
  if (!t) return "";
  return t.replace("FULLTIME", "Full-time").replace("PARTTIME", "Part-time").replace("CONTRACTOR", "Contract").replace("INTERN", "Internship");
}

function _esc(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
