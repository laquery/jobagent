/**
 * app.js — Main entry point: router, nav, global utilities, search overlay.
 */

import { renderDashboard } from "./views/dashboard.js";
import { renderJobs }      from "./views/jobs.js";
import { renderKanban }    from "./views/kanban.js";
import { closePanel }      from "./views/modal.js";
import { api }             from "./api.js";

// ── Routing ──────────────────────────────────────────────────────────────────

const VIEWS = {
  dashboard: { render: renderDashboard, el: "view-dashboard" },
  jobs:      { render: renderJobs,      el: "view-jobs"      },
  pipeline:  { render: renderKanban,    el: "view-pipeline"  },
};

let _currentView = null;

function navigate(hash) {
  const viewName = (hash || "").replace("#", "") || "dashboard";
  const view = VIEWS[viewName] || VIEWS.dashboard;

  // Update nav active state
  document.querySelectorAll(".nav-link").forEach(a => {
    a.classList.toggle("active", a.getAttribute("href") === "#" + viewName || (viewName === "dashboard" && a.getAttribute("href") === "#dashboard"));
  });

  // Hide all views, show target
  Object.values(VIEWS).forEach(v => {
    document.getElementById(v.el)?.classList.add("hidden");
  });
  document.getElementById(view.el)?.classList.remove("hidden");

  _currentView = viewName;
  view.render();
}

window.addEventListener("hashchange", () => navigate(location.hash));

// Initial load
navigate(location.hash || "#dashboard");


// ── Keyboard shortcuts ───────────────────────────────────────────────────────

document.addEventListener("keydown", e => {
  if (e.key === "Escape") closePanel();
});

// Close panel when overlay is clicked
document.getElementById("overlay")?.addEventListener("click", closePanel);


// ── Live Search ──────────────────────────────────────────────────────────────

let _searchPollTimer = null;

document.getElementById("btn-new-search")?.addEventListener("click", async () => {
  const overlay    = document.getElementById("search-overlay");
  const progressEl = document.getElementById("search-progress-text");
  const dismissBtn = document.getElementById("btn-search-dismiss");
  const spinner    = overlay.querySelector(".spinner");

  overlay.classList.remove("hidden");
  if (spinner)    spinner.style.display = "block";
  if (dismissBtn) dismissBtn.style.display = "none";
  if (progressEl) progressEl.textContent = "Starting up…";

  try {
    await api.startSearch();
    _pollSearch();
  } catch (err) {
    if (progressEl) progressEl.textContent = "Error: " + err.message;
    if (spinner)    spinner.style.display = "none";
    if (dismissBtn) dismissBtn.style.display = "block";
  }
});

document.getElementById("btn-search-dismiss")?.addEventListener("click", () => {
  document.getElementById("search-overlay")?.classList.add("hidden");
  clearTimeout(_searchPollTimer);
  // Refresh current view
  navigate("#" + (_currentView || "dashboard"));
});

function _pollSearch() {
  const overlay    = document.getElementById("search-overlay");
  const progressEl = document.getElementById("search-progress-text");
  const dismissBtn = document.getElementById("btn-search-dismiss");
  const spinner    = overlay?.querySelector(".spinner");

  _searchPollTimer = setTimeout(async () => {
    try {
      const state = await api.getSearchStatus();
      if (progressEl) progressEl.textContent = state.progress || "…";

      if (state.running) {
        _pollSearch(); // keep polling
      } else {
        if (spinner)    spinner.style.display = "none";
        if (dismissBtn) dismissBtn.style.display = "block";
        if (state.added > 0) {
          showToast(`Search complete — ${state.added} new jobs added!`, "success");
        } else if (state.found > 0) {
          showToast(`Search complete — no new jobs (${state.found} already saved)`, "info");
        }
        // Update jobs count badge
        try {
          const jobs = await api.getJobs({ limit: 1 });
          // Actually get total count
        } catch (_) {}
      }
    } catch (_) {
      _pollSearch();
    }
  }, 2000);
}


// ── Exported utilities used by view modules ───────────────────────────────────

/** Show a toast notification */
export function showToast(message, type = "info") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.className   = `toast toast-${type} show`;
  el.classList.remove("hidden");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.classList.add("hidden"), 210);
  }, 3200);
}

/** Return CSS class for a score value */
export function scoreClass(score) {
  if (score >= 10) return "score-high";
  if (score >= 5)  return "score-mid";
  return "score-low";
}

/** Return an HTML status badge string */
export function statusBadge(status) {
  const label = {
    saved: "Saved", applied: "Applied", followed_up: "Followed Up",
    interview: "Interview", offer: "Offer", rejected: "Rejected",
    declined: "Declined", withdrawn: "Withdrawn",
  }[status] || status || "Saved";
  const cls = status || "saved";
  return `<span class="status-badge status-${cls}">${label}</span>`;
}

/** Convert ISO date string to relative time */
export function timeAgo(dateStr) {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  if (isNaN(date)) return dateStr.slice(0, 10);
  const diffMs  = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1)   return "just now";
  if (diffMin < 60)  return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24)   return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7)   return `${diffDay}d ago`;
  const diffWk = Math.floor(diffDay / 7);
  if (diffWk < 5)    return `${diffWk}w ago`;
  const diffMo = Math.floor(diffDay / 30);
  if (diffMo < 12)   return `${diffMo}mo ago`;
  return `${Math.floor(diffMo / 12)}y ago`;
}
