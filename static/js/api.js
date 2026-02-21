/**
 * api.js — Thin fetch() wrapper for all JobAgent API calls.
 * All functions return parsed JSON or throw an Error.
 */

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  /** GET /api/jobs — returns array of job objects */
  getJobs(params = {}) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null))
    );
    return apiFetch("/api/jobs" + (qs.toString() ? "?" + qs : ""));
  },

  /** GET /api/jobs/:id — single job with full description */
  getJob(id) {
    return apiFetch(`/api/jobs/${id}`);
  },

  /** POST /api/jobs/:id/status — update application status */
  setStatus(id, status, notes = "") {
    return apiFetch(`/api/jobs/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status, notes }),
    });
  },

  /** PATCH /api/jobs/:id/notes — update notes only */
  updateNotes(id, notes) {
    return apiFetch(`/api/jobs/${id}/notes`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  },

  /** GET /api/stats */
  getStats() {
    return apiFetch("/api/stats");
  },

  /** GET /api/applications[?status=] */
  getApplications(status = "") {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiFetch("/api/applications" + qs);
  },

  /** GET /api/config */
  getConfig() {
    return apiFetch("/api/config");
  },

  /** POST /api/search — start background job search */
  startSearch(role = "") {
    return apiFetch("/api/search", {
      method: "POST",
      body: JSON.stringify(role ? { role } : {}),
    });
  },

  /** GET /api/search/status — poll search progress */
  getSearchStatus() {
    return apiFetch("/api/search/status");
  },
};
