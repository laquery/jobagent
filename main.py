"""
Job Agent CLI — search for design jobs and track applications.

Usage:
    python main.py search              Search all sources for matching jobs
    python main.py search --role "UX"  Search for a specific role
    python main.py links               Open job board search URLs in browser
    python main.py jobs                List saved jobs
    python main.py jobs --search figma Filter saved jobs by keyword
    python main.py apply <job_id>      Mark a job as applied
    python main.py status <job_id> <status>  Update application status
    python main.py track               View all tracked applications
    python main.py track --status applied    Filter by status
    python main.py detail <job_id>     Show full details for a job
    python main.py stats               View application statistics
    python main.py export              Export jobs to CSV
"""

import csv
import webbrowser

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config
import searcher
import tracker

console = Console()


@click.group()
def cli():
    """Job Agent — Find and track design job applications."""
    tracker.init_db()


# ── Search ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--role", "-r", default=None, help="Search for a specific role (default: all target roles)")
def search(role):
    """Search job boards for matching positions."""
    roles = [role] if role else config.TARGET_ROLES

    console.print(Panel.fit(
        f"[bold cyan]Searching for jobs...[/]\n"
        f"Roles: {', '.join(roles)}\n"
        f"Sources: {', '.join(name for name, _ in searcher.ALL_SOURCES)}",
        title="Job Search",
    ))

    results = searcher.search_all(roles)

    if not results:
        console.print("[yellow]No jobs found. Try adding API keys in config.py for more sources.[/]")
        _print_api_key_help()
        return

    # Save to database
    added = tracker.save_jobs(results)

    console.print(f"\n[green]Found {len(results)} jobs, {added} new.[/]\n")

    # Display results
    _display_jobs_table(results[:30])

    console.print(f"\n[dim]Jobs saved to database. Use [bold]python main.py jobs[/bold] to view all saved jobs.[/]")
    console.print(f"[dim]Use [bold]python main.py apply <id>[/bold] to mark a job as applied.[/]")


# ── Direct Search Links ──────────────────────────────────────────────────────

@cli.command()
@click.option("--role", "-r", default=None, help="Role to search for (default: all target roles)")
@click.option("--open", "-o", "open_browser", is_flag=True, help="Open URLs in browser")
def links(role, open_browser):
    """Generate direct search URLs for major job boards."""
    roles = [role] if role else config.TARGET_ROLES

    for r in roles:
        urls = searcher.generate_search_urls(r)
        console.print(f"\n[bold cyan]{r}[/]")
        for entry in urls:
            console.print(f"  [{entry['platform']}] {entry['url']}")
            if open_browser:
                webbrowser.open(entry["url"])

    if not open_browser:
        console.print(
            "\n[dim]Tip: Run with --open to open all links in your browser.[/]"
        )


# ── List Jobs ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--search", "-s", "keyword", default=None, help="Filter by keyword")
@click.option("--limit", "-l", default=50, help="Max results to show")
@click.option("--min-score", default=0, help="Minimum relevance score")
def jobs(keyword, limit, min_score):
    """List saved jobs from the database."""
    if keyword:
        results = tracker.search_jobs_db(keyword)
        console.print(f"[cyan]Jobs matching '{keyword}':[/]\n")
    else:
        results = tracker.get_jobs(limit=limit, min_score=min_score)
        console.print(f"[cyan]Saved jobs (top {limit}, min score {min_score}):[/]\n")

    if not results:
        console.print("[yellow]No jobs found. Run 'python main.py search' first.[/]")
        return

    _display_jobs_table(results)


# ── Job Detail ───────────────────────────────────────────────────────────────

@cli.command()
@click.argument("job_id", type=int)
def detail(job_id):
    """Show full details for a specific job."""
    job = tracker.get_job(job_id)
    if not job:
        console.print(f"[red]Job #{job_id} not found.[/]")
        return

    remote_label = "[green]Remote[/]" if job.get("is_remote") else job.get("location", "")
    status_label = f" | Status: [cyan]{job['app_status']}[/]" if job.get("app_status") else ""

    console.print(Panel.fit(
        f"[bold]{job['title']}[/]\n"
        f"[cyan]{job['company']}[/]  |  {job.get('location', '')}  {remote_label}"
        f"{status_label}",
        title=f"Job #{job_id}",
    ))

    # Key facts table
    info = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    info.add_column("Field", style="bold dim", width=20)
    info.add_column("Value")

    info.add_row("Source",          job.get("source", "—"))
    info.add_row("Posted",          job.get("date_posted", "—") or "—")
    info.add_row("Employment Type", job.get("employment_type", "—") or "—")
    info.add_row("Salary",          job.get("salary", "—") or "—")
    info.add_row("Experience",      job.get("experience_level", "—") or "—")
    info.add_row("Deadline",        job.get("apply_deadline", "—") or "—")
    info.add_row("Score",           str(job.get("score", 0)))
    info.add_row("Apply URL",       job.get("url", "—") or "—")

    if job.get("app_notes"):
        info.add_row("Notes", job["app_notes"])
    if job.get("applied_at"):
        info.add_row("Applied on", job["applied_at"][:10])
    if job.get("followed_up"):
        info.add_row("Followed up", job["followed_up"][:10])
    if job.get("interview_at"):
        info.add_row("Interview", job["interview_at"][:10])

    console.print(info)

    # Description
    if job.get("description"):
        console.print("\n[bold]Description:[/]")
        console.print(job["description"][:1500])

    console.print(
        f"\n[dim]To apply: [bold]python main.py apply {job_id}[/bold]  |  "
        f"To update status: [bold]python main.py status {job_id} <status>[/bold][/]"
    )


# ── Apply ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("job_id", type=int)
@click.option("--notes", "-n", default="", help="Add notes about the application")
def apply(job_id, notes):
    """Mark a job as applied."""
    success = tracker.set_status(job_id, "applied", notes)
    if success:
        console.print(f"[green]Job #{job_id} marked as applied![/]")
    else:
        console.print(f"[red]Failed to update job #{job_id}.[/]")


# ── Update Status ────────────────────────────────────────────────────────────

@cli.command()
@click.argument("job_id", type=int)
@click.argument("new_status", type=click.Choice(tracker.VALID_STATUSES))
@click.option("--notes", "-n", default="", help="Add notes")
def status(job_id, new_status, notes):
    """Update the status of a job application."""
    success = tracker.set_status(job_id, new_status, notes)
    if success:
        console.print(f"[green]Job #{job_id} status updated to '{new_status}'.[/]")
    else:
        console.print(f"[red]Failed to update job #{job_id}.[/]")


# ── Track Applications ──────────────────────────────────────────────────────

@cli.command()
@click.option("--status", "-s", "filter_status", default=None,
              type=click.Choice(tracker.VALID_STATUSES),
              help="Filter by application status")
def track(filter_status):
    """View all tracked applications."""
    apps = tracker.get_applications(filter_status)

    if not apps:
        console.print("[yellow]No tracked applications yet.[/]")
        console.print("[dim]Use 'python main.py apply <job_id>' to start tracking.[/]")
        return

    table = Table(title="Application Tracker", show_lines=True)
    table.add_column("ID", style="dim", width=5)
    table.add_column("Title", style="bold", max_width=35)
    table.add_column("Company", style="cyan", max_width=20)
    table.add_column("Status", max_width=12)
    table.add_column("Applied", max_width=12)
    table.add_column("Notes", max_width=30)

    status_colors = {
        "saved": "white",
        "applied": "blue",
        "followed_up": "yellow",
        "interview": "green",
        "offer": "bold green",
        "rejected": "red",
        "declined": "dim",
        "withdrawn": "dim",
    }

    for app in apps:
        color = status_colors.get(app["status"], "white")
        applied_date = (app.get("applied_at") or "")[:10]
        table.add_row(
            str(app["id"]),
            app["title"],
            app["company"],
            f"[{color}]{app['status']}[/]",
            applied_date,
            app.get("notes", "") or "",
        )

    console.print(table)


# ── Re-extract deadlines & experience for existing jobs ─────────────────────

@cli.command("update-details")
def update_details():
    """Re-extract deadlines and experience level from saved job descriptions."""
    all_jobs = tracker.get_jobs(limit=9999)
    updated = 0
    for job in all_jobs:
        desc = job.get("description", "") or ""
        deadline = searcher._extract_deadline(desc)
        exp = searcher._extract_experience(f"{job['title']} {desc}")
        if deadline or exp:
            tracker.update_job_fields(job["id"], {
                "apply_deadline": deadline,
                "experience_level": exp,
            })
            updated += 1
    console.print(f"[green]Updated details for {updated} jobs.[/]")


# ── Stats ────────────────────────────────────────────────────────────────────

@cli.command()
def stats():
    """View application statistics."""
    s = tracker.get_stats()

    table = Table(title="Job Search Stats", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Count", style="cyan", justify="right")

    table.add_row("Total jobs found", str(s.get("total_jobs_found", 0)))
    table.add_row("Saved (not applied)", str(s.get("saved", 0)))
    table.add_row("Applied", str(s.get("applied", 0)))
    table.add_row("Followed up", str(s.get("followed_up", 0)))
    table.add_row("Interviews", str(s.get("interview", 0)))
    table.add_row("Offers", str(s.get("offer", 0)))
    table.add_row("Rejected", str(s.get("rejected", 0)))

    console.print(table)


# ── Export to CSV ────────────────────────────────────────────────────────────

@cli.command()
@click.option("--output", "-o", default="jobs_export.csv", help="Output CSV filename")
def export(output):
    """Export all saved jobs to a CSV file."""
    all_jobs = tracker.get_jobs(limit=9999)
    if not all_jobs:
        console.print("[yellow]No jobs to export.[/]")
        return

    fieldnames = ["id", "title", "company", "location", "url", "date_posted",
                  "source", "salary", "salary_min", "salary_max",
                  "employment_type", "is_remote", "experience_level", "apply_deadline",
                  "score", "app_status", "app_notes"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_jobs)

    console.print(f"[green]Exported {len(all_jobs)} jobs to {output}[/]")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _display_jobs_table(jobs: list[dict]):
    table = Table(show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Score", style="magenta", width=5, justify="right")
    table.add_column("Title", style="bold", max_width=30)
    table.add_column("Company", style="cyan", max_width=18)
    table.add_column("Location", max_width=16)
    table.add_column("Type", max_width=10)
    table.add_column("Salary", style="green", max_width=16)
    table.add_column("Exp", max_width=10)
    table.add_column("Posted", max_width=11)
    table.add_column("Deadline", style="yellow", max_width=11)

    for job in jobs:
        job_id = str(job.get("id", "—"))
        remote = "[green]Remote[/]" if job.get("is_remote") else ""
        location = remote or job.get("location", "")
        emp_type = (job.get("employment_type") or "").replace("FULLTIME", "Full-time").replace("PARTTIME", "Part-time")
        table.add_row(
            job_id,
            str(job.get("score", 0)),
            job["title"],
            job["company"],
            location,
            emp_type,
            job.get("salary", "") or "",
            job.get("experience_level", "") or "",
            job.get("date_posted", "") or "",
            job.get("apply_deadline", "") or "",
        )

    console.print(table)


def _print_api_key_help():
    console.print(Panel.fit(
        "[bold]Add free API keys for more results:[/]\n\n"
        "1. [cyan]JSearch[/] (LinkedIn, Indeed, Glassdoor aggregator):\n"
        "   Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch\n"
        "   Add to config.py: JSEARCH_API_KEY = 'your_key'\n\n"
        "2. [cyan]Adzuna[/] (broad US job coverage):\n"
        "   Sign up at: https://developer.adzuna.com/\n"
        "   Add to config.py: ADZUNA_APP_ID / ADZUNA_APP_KEY\n",
        title="Boost Your Results",
    ))


if __name__ == "__main__":
    cli()
