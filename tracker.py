"""
Application tracker — SQLite-backed database to track job applications.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import config

DB_PATH = Path(config.DATABASE_PATH)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the tables if they don't exist, and migrate existing ones."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            company          TEXT NOT NULL,
            location         TEXT,
            url              TEXT UNIQUE,
            date_posted      TEXT,
            source           TEXT,
            salary           TEXT,
            salary_min       TEXT,
            salary_max       TEXT,
            employment_type  TEXT,
            is_remote        INTEGER DEFAULT 0,
            experience_level TEXT,
            apply_deadline   TEXT,
            description      TEXT,
            score            INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS applications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id       INTEGER NOT NULL REFERENCES jobs(id),
            status       TEXT NOT NULL DEFAULT 'saved',
            notes        TEXT,
            applied_at   TEXT,
            followed_up  TEXT,
            interview_at TEXT,
            updated_at   TEXT DEFAULT (datetime('now')),
            UNIQUE(job_id)
        );
    """)

    # Migrate: add new columns to existing tables if they don't exist yet
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    migrations = {
        "salary_min":       "ALTER TABLE jobs ADD COLUMN salary_min TEXT",
        "salary_max":       "ALTER TABLE jobs ADD COLUMN salary_max TEXT",
        "employment_type":  "ALTER TABLE jobs ADD COLUMN employment_type TEXT",
        "is_remote":        "ALTER TABLE jobs ADD COLUMN is_remote INTEGER DEFAULT 0",
        "experience_level": "ALTER TABLE jobs ADD COLUMN experience_level TEXT",
        "apply_deadline":   "ALTER TABLE jobs ADD COLUMN apply_deadline TEXT",
    }
    for col, sql in migrations.items():
        if col not in existing:
            conn.execute(sql)

    conn.commit()
    conn.close()


# ── Jobs ─────────────────────────────────────────────────────────────────────

def save_jobs(jobs: list[dict]) -> int:
    """Insert jobs into the database. Returns count of newly added jobs."""
    conn = _connect()
    added = 0
    for job in jobs:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (title, company, location, url, date_posted, source,
                    salary, salary_min, salary_max,
                    employment_type, is_remote, experience_level, apply_deadline,
                    description, score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job["title"],
                    job["company"],
                    job["location"],
                    job["url"],
                    job["date_posted"],
                    job["source"],
                    job.get("salary", ""),
                    job.get("salary_min", ""),
                    job.get("salary_max", ""),
                    job.get("employment_type", ""),
                    1 if job.get("is_remote") else 0,
                    job.get("experience_level", ""),
                    job.get("apply_deadline", ""),
                    job.get("description", ""),
                    job.get("score", 0),
                ),
            )
            if conn.total_changes:
                added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return added


def get_jobs(limit: int = 50, min_score: int = 0) -> list[dict]:
    """Retrieve saved jobs, sorted by score."""
    conn = _connect()
    rows = conn.execute(
        """SELECT j.*, a.status as app_status, a.notes as app_notes
           FROM jobs j
           LEFT JOIN applications a ON a.job_id = j.id
           WHERE j.score >= ?
           ORDER BY j.score DESC, j.created_at DESC
           LIMIT ?""",
        (min_score, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job(job_id: int) -> dict | None:
    """Get a single job by ID with full details."""
    conn = _connect()
    row = conn.execute(
        """SELECT j.*, a.status as app_status, a.notes as app_notes,
                  a.applied_at, a.followed_up, a.interview_at
           FROM jobs j
           LEFT JOIN applications a ON a.job_id = j.id
           WHERE j.id = ?""",
        (job_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search_jobs_db(keyword: str) -> list[dict]:
    """Search saved jobs by keyword."""
    conn = _connect()
    pattern = f"%{keyword}%"
    rows = conn.execute(
        """SELECT j.*, a.status as app_status
           FROM jobs j
           LEFT JOIN applications a ON a.job_id = j.id
           WHERE j.title LIKE ? OR j.company LIKE ? OR j.description LIKE ?
           ORDER BY j.score DESC""",
        (pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Applications ─────────────────────────────────────────────────────────────

VALID_STATUSES = [
    "saved",        # Found, not yet applied
    "applied",      # Application submitted
    "followed_up",  # Sent a follow-up
    "interview",    # Interview scheduled
    "offer",        # Received an offer
    "rejected",     # Got rejected
    "declined",     # Declined by me
    "withdrawn",    # Withdrew application
]


def set_status(job_id: int, status: str, notes: str = "") -> bool:
    """Set application status for a job."""
    if status not in VALID_STATUSES:
        return False
    conn = _connect()
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO applications (job_id, status, notes, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(job_id) DO UPDATE SET
               status = excluded.status,
               notes = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE applications.notes END,
               updated_at = excluded.updated_at""",
        (job_id, status, notes, now),
    )

    if status == "applied":
        conn.execute(
            "UPDATE applications SET applied_at = ? WHERE job_id = ?", (now, job_id)
        )
    elif status == "followed_up":
        conn.execute(
            "UPDATE applications SET followed_up = ? WHERE job_id = ?", (now, job_id)
        )
    elif status == "interview":
        conn.execute(
            "UPDATE applications SET interview_at = ? WHERE job_id = ?", (now, job_id)
        )

    conn.commit()
    conn.close()
    return True


def get_applications(status: str | None = None) -> list[dict]:
    """Get all tracked applications, optionally filtered by status."""
    conn = _connect()
    if status:
        rows = conn.execute(
            """SELECT j.id, j.title, j.company, j.location, j.url, j.score,
                      j.date_posted, j.employment_type, j.is_remote,
                      a.status, a.notes, a.applied_at, a.followed_up, a.interview_at, a.updated_at
               FROM applications a
               JOIN jobs j ON j.id = a.job_id
               WHERE a.status = ?
               ORDER BY a.updated_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT j.id, j.title, j.company, j.location, j.url, j.score,
                      j.date_posted, j.employment_type, j.is_remote,
                      a.status, a.notes, a.applied_at, a.followed_up, a.interview_at, a.updated_at
               FROM applications a
               JOIN jobs j ON j.id = a.job_id
               ORDER BY a.updated_at DESC""",
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_fields(job_id: int, fields: dict) -> None:
    """Update specific fields on an existing job row."""
    conn = _connect()
    for col, val in fields.items():
        try:
            conn.execute(f"UPDATE jobs SET {col} = ? WHERE id = ?", (val, job_id))
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get summary statistics of all applications."""
    conn = _connect()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
    ).fetchall()
    conn.close()
    stats = {"total_jobs_found": total_jobs}
    for r in rows:
        stats[r["status"]] = r["cnt"]
    return stats
