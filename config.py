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
    "design", "designer", "ux", "ui", "user experience", "user interface",
    "product design", "visual", "brand", "creative", "graphic",
    "marketing", "content", "researcher", "research",
    "front-end", "frontend", "front end",
    "illustrat",  # illustrator / illustration
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

# ── Search Settings ──────────────────────────────────────────────────────────
MAX_RESULTS_PER_SOURCE = 25
DATABASE_PATH = "jobagent.db"
