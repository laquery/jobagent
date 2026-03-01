"""
Configuration for Ramya Sandadi's job search agent.
"""

# ── Profile ──────────────────────────────────────────────────────────────────
PROFILE = {
    "name": "Ramya Sandadi",
    "email": "ramya_sandadi@hotmail.com",
    "phone": "425-442-3685",
    "portfolio": "https://ramyasandadi.com/",
    "linkedin": "https://linkedin.com/in/ramya-sandadi-800085240",
    "location": "Seattle, WA",
    "us_citizen": True,
    "summary": (
        "UI/UX Designer with 4+ years of experience creating accessible "
        "interactive solutions. Background includes Figma, UX/UI design, "
        "data visualization, user research, graphic design, and interactive "
        "web/mobile projects."
    ),
}

# ── Target Roles ─────────────────────────────────────────────────────────────
TARGET_ROLES = [
    "UX UI Designer",
    "Product Designer",
    "Visual Designer",
    "Brand Designer",
    "Marketing Designer",
    "UX Researcher",
    "UX Designer",
]

# ── Location Preferences ─────────────────────────────────────────────────────
LOCATIONS = [
    "Remote",
    "United States",
    "Seattle, WA",
    "San Francisco, CA",
    "New York, NY",
    "Los Angeles, CA",
    "Austin, TX",
    "Chicago, IL",
    "Boston, MA",
    "Portland, OR",
]

# ── Keywords that match Ramya's skills (used to score relevance) ─────────────
SKILL_KEYWORDS = [
    "figma", "adobe", "illustrator", "photoshop", "indesign",
    "wireframing", "prototyping", "user research", "usability testing",
    "accessibility", "data visualization", "design systems",
    "html", "css", "javascript", "responsive",
    "branding", "graphic design", "logo", "typography",
    "information architecture", "interaction design",
    "user-centered design", "persona", "journey mapping",
    "canva", "squarespace", "wordpress",
    "social media", "seo", "digital marketing", "content strategy",
    "a/b testing", "analytics",
]

# ── API Keys (add your free keys here for more results) ──────────────────────
# JSearch: Sign up free at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
JSEARCH_API_KEY = "44ba00c106msh5badca9a57fc263p12ed5ajsn0647ec8f066d"

# Adzuna: Sign up free at https://developer.adzuna.com/
ADZUNA_APP_ID = ""
ADZUNA_APP_KEY = ""

# The Muse: Sign up free at https://www.themuse.com/developers/api/v2
THE_MUSE_API_KEY = ""

# ── Title relevance filter ───────────────────────────────────────────────────
# Job title must contain at least one of these to be kept.
# This prevents "Software Engineer" etc. from slipping through when API
# descriptions happen to mention "product", "visual", etc.
RELEVANT_TITLE_KEYWORDS = [
    "design", "designer", "user experience", "user interface",
    "product design", "visual design", "brand design",
    "creative", "graphic",
    "marketing design", "content design", "content strateg",
    "front-end", "frontend", "front end",
    "illustrat",  # illustrator / illustration
]
# Short keywords (ux, ui) matched as whole words, not substrings
RELEVANT_TITLE_KEYWORDS_WORD = ["ux", "ui"]

# ── Title exclusion filter ──────────────────────────────────────────────────
# If a job title contains ANY of these, reject it even if it matches above.
# This removes hardware designers, software engineers, recruiters, etc.
EXCLUDED_TITLE_KEYWORDS = [
    "software engineer", "data engineer", "devops", "sre ",
    "backend", "fullstack", "full-stack", "full stack",
    "network engineer", "network asic", "asic ", "hardware",
    "electrical engineer", "mechanical engineer", "civil engineer",
    "talent acquisition", "recruiter", "recruiting",
    "sales rep", "account executive", "account manager",
    "game design", "game designer",
    "instructional design",
    "interior design",
    "fashion design",
    "floral design",
    "landscape design",
    "content reviewer", "content moderator",
    "data analyst", "data scientist", "machine learning",
    "security engineer", "reliability engineer",
    "project manager", "program manager", "product manager",
    "copywriter", "copy editor",
    "photographer",
]

# ── Seniority filter (based on ~4 years experience) ─────────────────────────
# Jobs whose TITLE contains any of these words get a score penalty so they
# sink below relevant results. They are NOT hidden — still visible if needed.
OVERQUALIFIED_TITLE_KEYWORDS = [
    "senior", "sr.",
    "principal",
    "staff",
    "lead",
    "head of",
    "director",
    "vp ", "vice president",
    "manager",
    "associate director",
]
# How many points to subtract per overqualified keyword found in the title
OVERQUALIFIED_PENALTY = 20

# ── Company Career Pages ─────────────────────────────────────────────────────
# Top tech & design companies with public job board APIs.
# "ats" is the applicant tracking system: "greenhouse" or "lever".
# "slug" is the company's board identifier.
COMPANY_BOARDS = [
    # Design-forward companies
    {"name": "Figma",        "ats": "greenhouse", "slug": "figma"},
    {"name": "Canva",        "ats": "greenhouse", "slug": "canva"},
    {"name": "Squarespace",  "ats": "greenhouse", "slug": "squarespace"},
    {"name": "Webflow",      "ats": "greenhouse", "slug": "webflow"},
    {"name": "Grammarly",    "ats": "greenhouse", "slug": "grammarly"},
    {"name": "Duolingo",     "ats": "greenhouse", "slug": "duolingo"},
    # Big tech
    {"name": "Stripe",       "ats": "greenhouse", "slug": "stripe"},
    {"name": "Airbnb",       "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Spotify",      "ats": "lever",      "slug": "spotify"},
    {"name": "Discord",      "ats": "greenhouse", "slug": "discord"},
    {"name": "Dropbox",      "ats": "greenhouse", "slug": "dropbox"},
    {"name": "Coinbase",     "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Cloudflare",   "ats": "greenhouse", "slug": "cloudflare"},
    {"name": "Databricks",   "ats": "greenhouse", "slug": "databricks"},
    {"name": "GitLab",       "ats": "greenhouse", "slug": "gitlab"},
    # Growth-stage
    {"name": "Intercom",     "ats": "greenhouse", "slug": "intercom"},
    {"name": "Asana",        "ats": "greenhouse", "slug": "asana"},
    {"name": "Brex",         "ats": "greenhouse", "slug": "brex"},
    {"name": "Plaid",        "ats": "lever",      "slug": "plaid"},
    {"name": "Robinhood",    "ats": "greenhouse", "slug": "robinhood"},
    {"name": "Affirm",       "ats": "greenhouse", "slug": "affirm"},
    {"name": "Gusto",        "ats": "greenhouse", "slug": "gusto"},
    {"name": "Lyft",         "ats": "greenhouse", "slug": "lyft"},
    {"name": "Instacart",    "ats": "greenhouse", "slug": "instacart"},
    {"name": "Vercel",       "ats": "greenhouse", "slug": "vercel"},
]

# ── Search Settings ──────────────────────────────────────────────────────────
MAX_RESULTS_PER_SOURCE = 25
DATABASE_PATH = "jobagent.db"
