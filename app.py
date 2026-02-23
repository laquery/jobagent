"""
JobAgent Web UI — Flask server + REST API.

Start with:
    python app.py

Opens http://localhost:5000 in your browser automatically.
The CLI (python main.py ...) continues to work alongside this server
since both share the same SQLite database.
"""

import os
import threading
import webbrowser
from flask import Flask, jsonify, request, render_template, abort

import config
import tracker
import searcher

app = Flask(__name__, template_folder="templates", static_folder="static")
tracker.init_db()

# ── Search background state ────────────────────────────────────────────────────
_search_state = {"running": False, "progress": "", "added": 0, "found": 0}
_search_lock = threading.Lock()


# ── SPA Shell ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.route("/api/jobs")
def api_jobs():
    q         = request.args.get("q", "").strip()
    status    = request.args.get("status", "").strip()
    min_score = int(request.args.get("min_score", 0))
    is_remote = request.args.get("is_remote", "")
    source    = request.args.get("source", "").strip()
    limit     = int(request.args.get("limit", 200))
    sort      = request.args.get("sort", "score")   # score | date | company

    if q:
        jobs = tracker.search_jobs_db(q)
    else:
        jobs = tracker.get_jobs(limit=limit, min_score=min_score)

    # Client-side filtering that tracker.py doesn't support natively
    if status:
        jobs = [j for j in jobs if (j.get("app_status") or "saved") == status]
    if is_remote == "1":
        jobs = [j for j in jobs if j.get("is_remote")]
    if source:
        jobs = [j for j in jobs if (j.get("source") or "").lower() == source.lower()]

    # Sort
    if sort == "date":
        jobs = sorted(jobs, key=lambda j: j.get("date_posted") or "", reverse=True)
    elif sort == "company":
        jobs = sorted(jobs, key=lambda j: (j.get("company") or "").lower())
    # default: already sorted by score from tracker

    return jsonify(jobs)


@app.route("/api/jobs/<int:job_id>")
def api_job_detail(job_id):
    job = tracker.get_job(job_id)
    if not job:
        abort(404)
    return jsonify(job)


@app.route("/api/jobs/<int:job_id>/status", methods=["POST"])
def api_set_status(job_id):
    data   = request.get_json(force=True)
    status = data.get("status", "")
    notes  = data.get("notes", "")

    if status not in tracker.VALID_STATUSES:
        return jsonify({"error": f"Invalid status '{status}'"}), 400

    ok = tracker.set_status(job_id, status, notes)
    if not ok:
        return jsonify({"error": "Failed to update"}), 500

    job = tracker.get_job(job_id)
    return jsonify({"ok": True, "status": status, "job": job})


@app.route("/api/jobs/<int:job_id>/notes", methods=["PATCH"])
def api_update_notes(job_id):
    data  = request.get_json(force=True)
    notes = data.get("notes", "")

    job = tracker.get_job(job_id)
    if not job:
        abort(404)

    current_status = job.get("app_status") or "saved"
    ok = tracker.set_status(job_id, current_status, notes)
    if not ok:
        return jsonify({"error": "Failed to update notes"}), 500

    return jsonify({"ok": True})


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(tracker.get_stats())


# ── Applications ──────────────────────────────────────────────────────────────

@app.route("/api/applications")
def api_applications():
    status = request.args.get("status", "").strip() or None
    apps   = tracker.get_applications(status)
    return jsonify(apps)


# ── Config (for frontend to know roles/sources) ───────────────────────────────

@app.route("/api/config")
def api_config():
    all_jobs = tracker.get_jobs(limit=9999, min_score=0)
    sources  = sorted({j.get("source") or "" for j in all_jobs if j.get("source")})
    return jsonify({
        "target_roles": config.TARGET_ROLES,
        "profile":      config.PROFILE,
        "statuses":     tracker.VALID_STATUSES,
        "sources":      sources,
    })


# ── Live Search ───────────────────────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def api_search():
    with _search_lock:
        if _search_state["running"]:
            return jsonify({"error": "Search already running"}), 409
        _search_state["running"]  = True
        _search_state["progress"] = "Starting search..."
        _search_state["added"]    = 0
        _search_state["found"]    = 0

    # Read request data HERE — request context won't exist inside the thread
    data = request.get_json(force=True, silent=True) or {}
    role = data.get("role")

    def _run(role):
        try:
            roles = [role] if role else config.TARGET_ROLES

            _search_state["progress"] = f"Searching {len(roles)} role(s) across all sources..."
            results = searcher.search_all(roles)

            _search_state["progress"] = f"Found {len(results)} jobs, saving..."
            added = tracker.save_jobs(results)

            with _search_lock:
                _search_state["found"]    = len(results)
                _search_state["added"]    = added
                _search_state["progress"] = f"Done! Found {len(results)}, {added} new."
                _search_state["running"]  = False
        except Exception as e:
            with _search_lock:
                _search_state["progress"] = f"Error: {e}"
                _search_state["running"]  = False

    t = threading.Thread(target=_run, args=(role,), daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Search started"})


@app.route("/api/search/status")
def api_search_status():
    return jsonify(dict(_search_state))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_local = port == 5000 and not os.environ.get("RAILWAY_ENVIRONMENT")

    if is_local:
        def _open_browser():
            webbrowser.open(f"http://localhost:{port}")
        threading.Timer(1.2, _open_browser).start()

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True, use_reloader=False)
