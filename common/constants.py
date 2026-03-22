"""Constants shared across the project."""

# ATS type detection by URL domain
ATS_DOMAIN_MAP: dict[str, str] = {
    "greenhouse.io": "Greenhouse",
    "boards.greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "jobs.lever.co": "Lever",
    "myworkdayjobs.com": "Workday",
    "myworkday.com": "Workday",
}

# Notion status values
class Status:
    QUEUED = "Queued"
    APPLIED = "Applied"
    EMAILED = "Emailed"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    FAILED = "Failed"
    MANUAL_REQUIRED = "Manual Required"

# Notion source values
class Source:
    EASY_APPLY = "LinkedIn Easy Apply"
    JOBSPY = "JobSpy"
    POST_OUTREACH = "Post Outreach"
    MANUAL = "Manual"


def detect_ats_type(url: str) -> str:
    """Detect ATS type from a job URL's domain."""
    from urllib.parse import urlparse

    domain = urlparse(url).hostname or ""
    for ats_domain, ats_type in ATS_DOMAIN_MAP.items():
        if ats_domain in domain:
            return ats_type
    return "Other"
