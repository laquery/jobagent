/**
 * views/kanban.js — Pipeline Kanban board.
 * Shows only jobs with an applications record (any status).
 */

import { api } from "../api.js";
import { openPanel } from "./modal.js";
import { showToast, statusBadge, scoreClass, timeAgo } from "../app.js";

const COLUMNS = [
  { status: "saved",        label: "Saved" },
  { status: "applied",      label: "Applied" },
  { status: "followed_up",  label: "Followed Up" },
  { status: "interview",    label: "Interview" },
  { status: "offer",        label: "Offer" },
  { status: "rejected",     label: "Rejected" },
  { status: "declined",     label: "Declined" },
];

export async function renderKanban() {
  const view = document.getElementById("view-pipeline");
  view.innerHTML = `
    <div class="view-header">
      <div class="view-title">Pipeline</div>
      <div class="view-subtitle">Drag cards or use the move menu to update application status</div>
    </div>
    <div class="kanban-board" id="kanban-board">
      ${COLUMNS.map(col => `
        <div class="kanban-col" data-status="${col.status}">
          <div class="kanban-col-header">
            <span class="kanban-col-title">${col.label}</span>
            <span class="kanban-col-count" id="col-count-${col.status}">0</span>
          </div>
          <div class="kanban-cards" id="col-${col.status}">
            <div class="skeleton" style="height:76px;border-radius:8px"></div>
          </div>
        </div>
      `).join("")}
    </div>
  `;

  try {
    const apps = await api.getApplications();
    _renderBoard(apps);
  } catch (err) {
    showToast("Failed to load pipeline: " + err.message, "error");
  }
}

function _renderBoard(apps) {
  // Group by status
  const byStatus = {};
  COLUMNS.forEach(c => (byStatus[c.status] = []));
  apps.forEach(app => {
    if (byStatus[app.status]) byStatus[app.status].push(app);
  });

  COLUMNS.forEach(col => {
    const cards   = byStatus[col.status] || [];
    const colEl   = document.getElementById(`col-${col.status}`);
    const countEl = document.getElementById(`col-count-${col.status}`);
    if (!colEl) return;

    countEl.textContent = cards.length;

    if (cards.length === 0) {
      colEl.innerHTML = `<div style="padding:16px 8px;text-align:center;font-size:12px;color:var(--color-text-faint)">No jobs here</div>`;
      return;
    }

    colEl.innerHTML = cards.map(app => _cardHtml(app, col.status)).join("");

    // Bind click + move menu events
    colEl.querySelectorAll(".kanban-card").forEach(card => {
      const id = parseInt(card.dataset.id);

      card.addEventListener("click", e => {
        if (e.target.closest(".kanban-move-btn") || e.target.closest(".kanban-move-menu")) return;
        openPanel(id);
      });
    });

    colEl.querySelectorAll(".kanban-move-btn").forEach(btn => {
      btn.addEventListener("click", e => {
        e.stopPropagation();
        const menu = btn.nextElementSibling;
        // Close all other open menus
        document.querySelectorAll(".kanban-move-menu.open").forEach(m => {
          if (m !== menu) m.classList.remove("open");
        });
        menu.classList.toggle("open");
      });
    });

    colEl.querySelectorAll(".kanban-move-item").forEach(item => {
      item.addEventListener("click", async e => {
        e.stopPropagation();
        const card      = item.closest(".kanban-card");
        const jobId     = parseInt(card.dataset.id);
        const newStatus = item.dataset.status;
        item.closest(".kanban-move-menu").classList.remove("open");

        try {
          await api.setStatus(jobId, newStatus);
          showToast(`Moved to ${_statusLabel(newStatus)}`, "success");
          // Reload the board
          const freshApps = await api.getApplications();
          _renderBoard(freshApps);
        } catch (err) {
          showToast("Move failed: " + err.message, "error");
        }
      });
    });
  });

  // Close menus when clicking outside
  document.addEventListener("click", () => {
    document.querySelectorAll(".kanban-move-menu.open").forEach(m => m.classList.remove("open"));
  }, { once: true });
}

function _cardHtml(app, currentStatus) {
  const remote = app.is_remote;
  const otherStatuses = COLUMNS.filter(c => c.status !== currentStatus);

  return `
    <div class="kanban-card" data-id="${app.id}" data-status="${currentStatus}">
      <div class="kanban-card-title">${_esc(app.title)}</div>
      <div class="kanban-card-company">${_esc(app.company)}${app.location ? " · " + _esc(app.location) : ""}</div>
      <div class="kanban-card-meta">
        <span class="score-dot ${scoreClass(app.score || 0)}" style="font-size:11px">${app.score || 0}</span>
        ${remote ? `<span class="tag-remote" style="font-size:10px">Remote</span>` : ""}
        <span class="kanban-card-time" style="margin-left:auto">${timeAgo(app.updated_at)}</span>
        <div style="position:relative">
          <button class="kanban-move-btn" title="Move to…" style="background:var(--color-surface-alt);border:1px solid var(--color-border);border-radius:4px;padding:2px 6px;font-size:11px;color:var(--color-text-muted);cursor:pointer;">
            Move ▾
          </button>
          <div class="kanban-move-menu" style="position:absolute;right:0;top:100%;margin-top:4px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);box-shadow:var(--shadow-lg);z-index:10;min-width:140px;display:none;flex-direction:column;">
            ${otherStatuses.map(s => `<button class="kanban-move-item" data-status="${s.status}" style="padding:8px 14px;text-align:left;border:none;background:none;cursor:pointer;font-size:12px;font-weight:500;color:var(--color-text);white-space:nowrap;" onmouseover="this.style.background='var(--color-surface-alt)'" onmouseout="this.style.background='none'">${s.label}</button>`).join("")}
          </div>
        </div>
      </div>
    </div>`;
}

// Make move menus work with CSS toggle
const style = document.createElement("style");
style.textContent = `.kanban-move-menu.open { display: flex !important; }`;
document.head.appendChild(style);

function _statusLabel(s) {
  return { saved: "Saved", applied: "Applied", followed_up: "Followed Up", interview: "Interview", offer: "Offer", rejected: "Rejected", declined: "Declined", withdrawn: "Withdrawn" }[s] || s;
}

function _esc(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
