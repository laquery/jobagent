"""
Job search module — queries multiple free job APIs and scores results by relevance.
Also generates direct search URLs for major job boards.
"""

import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import requests

import config


def _extract_deadline(text: str) -> str:
    """Try to find an application deadline in job description text."""
    patterns = [
        # "close on: 02/20/2026" / "close on: February 20, 2026"
        r"(?:apply|application|deadline|closes?|closing|due|window)\s+(?:\w+\s+){0,4}(?:by|before|on|date)[:\s]+\s*([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})",
        r"(?:apply|application|deadline|closes?|closing|due|window)\s+(?:\w+\s+){0,4}(?:by|before|on|date)[:\s]+\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        # "application deadline: Feb 20, 2026"
        r"(?:application\s+(?:deadline|window)|closing\s+date|apply\s+by|posted\s+until)[:\s]+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})",
        r"(?:application\s+(?:deadline|window)|closing\s+date|apply\s+by|posted\s+until)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        # "expected to close on: 02/20/2026"
        r"expected\s+to\s+close\s+on[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"expected\s+to\s+close\s+on[:\s]+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_experience(text: str) -> str:
    """Try to extract required experience level from job text."""
    text_lower = text.lower()
    patterns = [
        (r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s+(?:of\s+)?experience", lambda m: f"{m.group(1)}+ yrs"),
        (r"entry[\s-]level", lambda m: "Entry Level"),
        (r"mid[\s-]level", lambda m: "Mid Level"),
        (r"senior|sr\.", lambda m: "Senior"),
        (r"principal|staff|lead", lambda m: "Principal/Staff"),
        (r"junior|jr\.", lambda m: "Junior"),
    ]
    for pattern, formatter in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return formatter(match)
    return ""


def _score_job(title: str, description: str) -> int:
    """Score a job listing based on how well it matches Ramya's skills."""
    text = f"{title} {description}".lower()
    score = 0
    for kw in config.SKILL_KEYWORDS:
        if kw in text:
            score += 1
    # Boost for exact role-title matches
    title_lower = title.lower()
    for role in config.TARGET_ROLES:
        if role.lower() in title_lower:
            score += 10
    # Penalise titles that are likely overqualified (~4 yrs experience)
    for kw in config.OVERQUALIFIED_TITLE_KEYWORDS:
        if kw in title_lower:
            score -= config.OVERQUALIFIED_PENALTY
            break  # one penalty max per job
    return score


def _is_relevant_title(title: str) -> bool:
    """Return True if the job title contains at least one design-related keyword
    and none of the excluded keywords."""
    title_lower = title.lower()
    if any(ex in title_lower for ex in config.EXCLUDED_TITLE_KEYWORDS):
        return False
    # Substring match for longer keywords
    if any(kw in title_lower for kw in config.RELEVANT_TITLE_KEYWORDS):
        return True
    # Whole-word match for short keywords (ux, ui) to avoid false positives
    for kw in config.RELEVANT_TITLE_KEYWORDS_WORD:
        if re.search(rf"\b{kw}\b", title_lower):
            return True
    return False


def _is_us_location(location: str) -> bool:
    """Return True if the location looks like US, Remote, or worldwide."""
    loc = location.lower().strip()
    if not loc:
        return True  # missing location — keep it
    us_indicators = [
        "united states", "usa", "u.s.", "us ",
        "remote", "anywhere", "worldwide", "global", "north america",
        # US states (abbreviations after comma, e.g. "Seattle, WA")
        ", al", ", ak", ", az", ", ar", ", ca", ", co", ", ct", ", de",
        ", fl", ", ga", ", hi", ", id", ", il", ", in", ", ia", ", ks",
        ", ky", ", la", ", me", ", md", ", ma", ", mi", ", mn", ", ms",
        ", mo", ", mt", ", ne", ", nv", ", nh", ", nj", ", nm", ", ny",
        ", nc", ", nd", ", oh", ", ok", ", or", ", pa", ", ri", ", sc",
        ", sd", ", tn", ", tx", ", ut", ", vt", ", va", ", wa", ", wv",
        ", wi", ", wy", ", dc",
    ]
    # Quick pass for obvious US / remote
    if any(indicator in loc for indicator in us_indicators):
        return True
    # Reject locations that name a non-US country
    non_us = [
        "romania", "germany", "india", "uk", "united kingdom", "canada",
        "brazil", "france", "spain", "italy", "netherlands", "australia",
        "poland", "portugal", "mexico", "argentina", "colombia", "chile",
        "japan", "china", "korea", "singapore", "israel", "turkey",
        "sweden", "norway", "denmark", "finland", "ireland", "austria",
        "switzerland", "belgium", "czech", "hungary", "ukraine", "russia",
        "philippines", "indonesia", "vietnam", "thailand", "malaysia",
        "south africa", "nigeria", "kenya", "egypt", "pakistan",
        "new zealand", "europe", "asia", "africa", "latin america",
        "emea", "apac",
    ]
    if any(country in loc for country in non_us):
        return False
    # If we can't tell, keep it (could be a city name we don't recognise)
    return True


def _matches_query(text: str, query: str) -> bool:
    """Check if text matches the query — at least one meaningful word must appear."""
    text_lower = text.lower()
    # Match on any word with 3+ chars (skip 'ux', 'ui' — handle those separately)
    words = query.lower().split()
    short_terms = [w for w in words if len(w) <= 2]
    long_terms = [w for w in words if len(w) > 2]
    # Check compound terms like "ux/ui", "ux designer"
    if query.lower().replace(" ", "") in text_lower.replace(" ", "").replace("/", ""):
        return True
    if any(w in text_lower for w in long_terms):
        return True
    if any(w in text_lower.split() for w in short_terms):
        return True
    return False


# ── Source: Remotive (free, no key, remote jobs) ─────────────────────────────

def search_remotive(query: str) -> list[dict]:
    """Search Remotive for remote design jobs."""
    url = "https://remotive.com/api/remote-jobs"
    # Fetch all jobs (no limit) and filter client-side
    params = {}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [Remotive] Error: {e}")
        return []

    results = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        desc = job.get("description", "")
        category = job.get("category", "").lower()
        tags = " ".join(job.get("tags", []))
        combined = f"{title} {desc} {category} {tags}"

        # Must match either the query or be in design/marketing category
        is_design_category = any(
            cat in category for cat in ["design", "marketing", "product"]
        )
        if not (_matches_query(combined, query) or (is_design_category and _matches_query(title, query))):
            continue

        location = job.get("candidate_required_location", "Anywhere")
        if not _is_us_location(location):
            continue

        clean_desc = re.sub(r"<[^>]+>", "", desc)
        results.append({
            "title": title,
            "company": job.get("company_name", ""),
            "location": location,
            "url": job.get("url", ""),
            "date_posted": job.get("publication_date", "")[:10],
            "source": "Remotive",
            "salary": job.get("salary", ""),
            "salary_min": "",
            "salary_max": "",
            "employment_type": job.get("job_type", ""),
            "is_remote": True,
            "experience_level": _extract_experience(f"{title} {clean_desc}"),
            "apply_deadline": _extract_deadline(clean_desc),
            "description": clean_desc[:1000],
            "score": _score_job(title, desc),
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: RemoteOK (free, no key) ──────────────────────────────────────────

def search_remoteok(query: str) -> list[dict]:
    """Search RemoteOK for remote jobs."""
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "JobAgent/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [RemoteOK] Error: {e}")
        return []

    results = []
    # First item is metadata, skip it
    for job in data[1:] if len(data) > 1 else []:
        if not isinstance(job, dict):
            continue
        title = job.get("position", "")
        desc = job.get("description", "")
        tags = " ".join(job.get("tags", []))
        combined = f"{title} {desc} {tags}"
        if not _matches_query(combined, query):
            continue
        location = job.get("location", "Remote")
        if not _is_us_location(location):
            continue
        clean_desc = re.sub(r"<[^>]+>", "", desc) if desc else ""
        results.append({
            "title": title,
            "company": job.get("company", ""),
            "location": location,
            "url": job.get("url", ""),
            "date_posted": job.get("date", "")[:10],
            "source": "RemoteOK",
            "salary": "",
            "salary_min": str(job.get("salary_min", "")),
            "salary_max": str(job.get("salary_max", "")),
            "employment_type": "Full-time",
            "is_remote": True,
            "experience_level": _extract_experience(f"{title} {clean_desc}"),
            "apply_deadline": _extract_deadline(clean_desc),
            "description": clean_desc[:1000],
            "score": _score_job(title, desc or ""),
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: The Muse (free, optional key) ────────────────────────────────────

def search_themuse(query: str) -> list[dict]:
    """Search The Muse for design jobs across multiple categories."""
    all_results = []
    # Query multiple relevant categories
    categories = ["Design", "Marketing & PR", "Project Management"]
    for cat in categories:
      for page in range(5):  # pages 0-4, ~20 results each
        url = "https://www.themuse.com/api/public/jobs"
        params = {"category": cat, "page": page}
        if config.THE_MUSE_API_KEY:
            params["api_key"] = config.THE_MUSE_API_KEY
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break  # stop paginating this category on error

        jobs = data.get("results", [])
        if not jobs:
            break  # no more pages

        for job in jobs:
            title = job.get("name", "")
            company = job.get("company", {}).get("name", "")
            desc = job.get("contents", "")
            locations = ", ".join(
                loc.get("name", "") for loc in job.get("locations", [])
            )
            combined = f"{title} {desc}"
            if not _matches_query(combined, query):
                continue
            if not _is_us_location(locations):
                continue
            clean_desc = re.sub(r"<[^>]+>", "", desc)
            levels = [lv.get("name", "") for lv in job.get("levels", [])]
            all_results.append({
                "title": title,
                "company": company,
                "location": locations or "See listing",
                "url": job.get("refs", {}).get("landing_page", ""),
                "date_posted": job.get("publication_date", "")[:10],
                "source": "The Muse",
                "salary": "",
                "salary_min": "",
                "salary_max": "",
                "employment_type": job.get("type", ""),
                "is_remote": "Flexible" in locations or "Remote" in locations,
                "experience_level": ", ".join(levels) if levels else _extract_experience(f"{title} {clean_desc}"),
                "apply_deadline": _extract_deadline(clean_desc),
                "description": clean_desc[:1000],
                "score": _score_job(title, desc),
            })
    return sorted(all_results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: Jobicy (free, no key, remote jobs) ───────────────────────────────

def search_jobicy(query: str) -> list[dict]:
    """Search Jobicy for remote jobs."""
    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"count": 50}
    headers = {"User-Agent": "Mozilla/5.0 (JobAgent/1.0)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [Jobicy] Error: {e}")
        return []

    results = []
    for job in data.get("jobs", []):
        title = job.get("jobTitle", "")
        desc = job.get("jobDescription", "")
        industry = job.get("jobIndustry", [])
        industry_str = " ".join(industry) if isinstance(industry, list) else str(industry)
        combined = f"{title} {desc} {industry_str}"
        if not _matches_query(combined, query):
            continue

        geo = job.get("jobGeo", "")
        if not _is_us_location(geo):
            continue

        clean_desc = re.sub(r"<[^>]+>", "", desc) if desc else ""
        sal_min = str(job.get("annualSalaryMin", ""))
        sal_max = str(job.get("annualSalaryMax", ""))
        results.append({
            "title": title,
            "company": job.get("companyName", ""),
            "location": geo or "Remote",
            "url": job.get("url", ""),
            "date_posted": job.get("pubDate", "")[:10],
            "source": "Jobicy",
            "salary": f"${sal_min}-${sal_max}" if sal_min else "",
            "salary_min": sal_min,
            "salary_max": sal_max,
            "employment_type": job.get("jobType", ""),
            "is_remote": True,
            "experience_level": _extract_experience(f"{title} {clean_desc}"),
            "apply_deadline": _extract_deadline(clean_desc),
            "description": clean_desc[:1000],
            "score": _score_job(title, desc or ""),
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: Himalayas (free, no key, remote jobs) ────────────────────────────

def search_himalayas(query: str) -> list[dict]:
    """Search Himalayas.app for remote jobs with offset pagination."""
    url = "https://himalayas.app/jobs/api"
    results = []
    for offset in range(0, 100, 20):  # pages of 20, up to 100 jobs
        params = {"limit": 20, "offset": offset}
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"  [Himalayas] Error: {e}")
            break

        jobs = data.get("jobs", [])
        if not jobs:
            break

        for job in jobs:
            title = job.get("title", "")
            desc = job.get("description", "")
            categories = " ".join(job.get("categories", []))
            combined = f"{title} {desc} {categories}"
            if not _matches_query(combined, query):
                continue

            location = ", ".join(job.get("locationRestrictions", [])) or "Remote"
            if not _is_us_location(location):
                continue

            clean_desc = re.sub(r"<[^>]+>", "", desc) if desc else ""
            sal_min = str(job.get("minSalary", ""))
            sal_max = str(job.get("maxSalary", ""))
            results.append({
                "title": title,
                "company": job.get("companyName", ""),
                "location": location,
                "url": job.get("applicationLink", "") or job.get("pageUrl", ""),
                "date_posted": str(job.get("pubDate", ""))[:10],
                "source": "Himalayas",
                "salary": f"${sal_min}-${sal_max}" if sal_min else "",
                "salary_min": sal_min,
                "salary_max": sal_max,
                "employment_type": job.get("jobType", ""),
                "is_remote": True,
                "experience_level": _extract_experience(f"{title} {clean_desc}"),
                "apply_deadline": _extract_deadline(clean_desc),
                "description": clean_desc[:1000],
                "score": _score_job(title, desc or ""),
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: JSearch / RapidAPI (free tier — needs key) ───────────────────────

def search_jsearch(query: str) -> list[dict]:
    """Search JSearch (RapidAPI) — aggregates LinkedIn, Indeed, Glassdoor."""
    if not config.JSEARCH_API_KEY:
        return []
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": config.JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {
        "query": f"{query} in United States",
        "page": "1",
        "num_pages": "3",
        "date_posted": "month",
        "remote_jobs_only": "false",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        if resp.status_code == 403:
            # Silently skip if not subscribed
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return []

    results = []
    for job in data.get("data", []):
        title = job.get("job_title", "")
        desc = job.get("job_description", "")
        city = job.get("job_city", "") or ""
        state = job.get("job_state", "") or ""
        location = f"{city} {state}".strip() or "See listing"
        sal_min = job.get("job_min_salary")
        sal_max = job.get("job_max_salary")
        sal_period = job.get("job_salary_period", "") or ""
        salary_str = ""
        if sal_min and sal_max:
            salary_str = f"${sal_min:,.0f}-${sal_max:,.0f} {sal_period}".strip()
        elif sal_min:
            salary_str = f"${sal_min:,.0f}+ {sal_period}".strip()
        exp = job.get("job_required_experience", {}) or {}
        exp_str = ""
        if exp.get("required_experience_in_months"):
            yrs = exp["required_experience_in_months"] // 12
            exp_str = f"{yrs}+ yrs"
        elif exp.get("experience_mentioned"):
            exp_str = _extract_experience(f"{title} {desc or ''}")
        results.append({
            "title": title,
            "company": job.get("employer_name", ""),
            "location": location,
            "url": job.get("job_apply_link", "") or job.get("job_google_link", ""),
            "date_posted": (job.get("job_posted_at_datetime_utc") or "")[:10],
            "source": "JSearch",
            "salary": salary_str,
            "salary_min": str(sal_min) if sal_min else "",
            "salary_max": str(sal_max) if sal_max else "",
            "employment_type": job.get("job_employment_type", "") or "",
            "is_remote": bool(job.get("job_is_remote")),
            "experience_level": exp_str or _extract_experience(f"{title} {desc or ''}"),
            "apply_deadline": _extract_deadline(desc or ""),
            "description": (desc or "")[:1000],
            "score": _score_job(title, desc or ""),
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: Adzuna (free tier — needs key) ───────────────────────────────────

def search_adzuna(query: str) -> list[dict]:
    """Search Adzuna for US design jobs across multiple pages."""
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        return []

    results = []
    for page in range(1, 4):  # pages 1-3
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
            f"?app_id={config.ADZUNA_APP_ID}"
            f"&app_key={config.ADZUNA_APP_KEY}"
            f"&results_per_page=50"
            f"&what={quote_plus(query)}"
            f"&content-type=application/json"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            if page == 1:
                print(f"  [Adzuna] Error: {e}")
            break

        jobs = data.get("results", [])
        if not jobs:
            break

        for job in jobs:
            title = job.get("title", "")
            desc = job.get("description", "")
            clean_desc = re.sub(r"<[^>]+>", "", desc)
            sal_min = job.get("salary_min")
            sal_max = job.get("salary_max")
            salary_str = f"${sal_min:,.0f}-${sal_max:,.0f}" if sal_min and sal_max else ""
            results.append({
                "title": re.sub(r"<[^>]+>", "", title),
                "company": job.get("company", {}).get("display_name", ""),
                "location": job.get("location", {}).get("display_name", ""),
                "url": job.get("redirect_url", ""),
                "date_posted": (job.get("created") or "")[:10],
                "source": "Adzuna",
                "salary": salary_str,
                "salary_min": str(sal_min) if sal_min else "",
                "salary_max": str(sal_max) if sal_max else "",
                "employment_type": job.get("contract_type", "") or "",
                "is_remote": False,
                "experience_level": _extract_experience(f"{title} {clean_desc}"),
                "apply_deadline": _extract_deadline(clean_desc),
                "description": clean_desc[:1000],
                "score": _score_job(title, desc),
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Source: We Work Remotely (free, RSS, design category) ────────────────────

def search_weworkremotely(query: str) -> list[dict]:
    """Search We Work Remotely design category via RSS feed."""
    url = "https://weworkremotely.com/categories/remote-design-jobs.rss"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"  [WWR] Error: {e}")
        return []

    results = []
    for item in root.findall(".//item"):
        raw_title = item.findtext("title", "")
        # Title format is "Company: Job Title"
        if ": " in raw_title:
            company, title = raw_title.split(": ", 1)
        else:
            company, title = "", raw_title

        desc = item.findtext("description", "") or ""
        region = item.findtext("region", "") or ""
        combined = f"{title} {desc}"
        if not _matches_query(combined, query):
            continue
        if not _is_us_location(region or "Remote"):
            continue

        clean_desc = re.sub(r"<[^>]+>", "", desc)
        link = item.findtext("link", "") or item.findtext("guid", "")
        pub_date = item.findtext("pubDate", "")
        # Parse "Thu, 26 Feb 2026 16:43:31 +0000" to "2026-02-26"
        date_posted = ""
        if pub_date:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub_date)
                date_posted = dt.strftime("%Y-%m-%d")
            except Exception:
                date_posted = pub_date[:16]

        emp_type = item.findtext("type", "") or ""
        results.append({
            "title": title.strip(),
            "company": company.strip(),
            "location": region or "Remote",
            "url": link,
            "date_posted": date_posted,
            "source": "WWR",
            "salary": "",
            "salary_min": "",
            "salary_max": "",
            "employment_type": emp_type,
            "is_remote": True,
            "experience_level": _extract_experience(f"{title} {clean_desc}"),
            "apply_deadline": _extract_deadline(clean_desc),
            "description": clean_desc[:1000],
            "score": _score_job(title, desc),
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)[
        : config.MAX_RESULTS_PER_SOURCE
    ]


# ── Main search orchestrator ─────────────────────────────────────────────────

ALL_SOURCES = [
    ("Remotive", search_remotive),
    ("RemoteOK", search_remoteok),
    ("The Muse", search_themuse),
    ("Jobicy", search_jobicy),
    ("Himalayas", search_himalayas),
    ("WWR", search_weworkremotely),
    ("JSearch", search_jsearch),
    ("Adzuna", search_adzuna),
]


def search_all(roles: list[str] | None = None) -> list[dict]:
    """Run searches across all sources for each target role. Returns deduplicated results."""
    if roles is None:
        roles = config.TARGET_ROLES

    seen_urls = set()
    all_results = []

    for role in roles:
        for source_name, search_fn in ALL_SOURCES:
            results = search_fn(role)
            for job in results:
                url = job.get("url", "")
                if url and url not in seen_urls and _is_relevant_title(job.get("title", "")):
                    seen_urls.add(url)
                    all_results.append(job)
            time.sleep(0.3)  # be polite to APIs

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results


# ── Direct Search URL Generator ──────────────────────────────────────────────

def generate_search_urls(role: str) -> list[dict]:
    """Generate direct search URLs for major job boards."""
    q = quote_plus(role)
    return [
        {
            "platform": "LinkedIn",
            "url": f"https://www.linkedin.com/jobs/search/?keywords={q}&location=United%20States&f_WT=2",
        },
        {
            "platform": "Indeed",
            "url": f"https://www.indeed.com/jobs?q={q}&l=Remote",
        },
        {
            "platform": "Glassdoor",
            "url": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}",
        },
        {
            "platform": "Dribbble",
            "url": f"https://dribbble.com/jobs?keyword={q}&location=Anywhere",
        },
        {
            "platform": "Wellfound",
            "url": f"https://wellfound.com/role/r/{role.lower().replace(' ', '-')}",
        },
        {
            "platform": "Built In",
            "url": f"https://builtin.com/jobs?search={q}",
        },
    ]
