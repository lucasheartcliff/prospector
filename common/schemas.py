"""Pydantic models for configuration and data records."""

from pydantic import BaseModel


# --- Config schemas ---

class SearchConfig(BaseModel):
    titles: list[str]
    locations: list[str]
    experience_level: str = "senior"


class LimitsConfig(BaseModel):
    easy_apply_daily: int = 25
    post_outreach_daily: int = 8
    claude_calls_daily: int = 200
    post_max_age_hours: int = 48
    hunter_min_confidence: int = 70


class ScheduleConfig(BaseModel):
    jobspy_cron: str = "0 8 * * *"
    easy_apply_cron: str = "0 9 * * *"
    post_scraper_cron: str = "0 10 * * *"


class AppConfig(BaseModel):
    search: SearchConfig
    limits: LimitsConfig = LimitsConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    n8n_webhook_url: str = "http://localhost:5678/webhook"
    server_port: int = 8100


# --- Answers schema ---

class PersonalInfo(BaseModel):
    full_name: str
    email: str
    phone: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class WorkInfo(BaseModel):
    years_experience: int
    current_company: str = ""
    availability: str = ""
    salary_expectation_usd: str = ""
    work_authorization: str = ""
    preferred_stack: list[str] = []


class AnswersData(BaseModel):
    willing_to_relocate: bool = True
    open_to_remote: bool = True
    requires_visa_sponsorship: bool = False
    cover_letter_default: str = ""


class AnswersConfig(BaseModel):
    personal: PersonalInfo
    work: WorkInfo
    answers: AnswersData = AnswersData()


# --- Blacklist schema ---

class BlacklistConfig(BaseModel):
    companies: list[str] = []


# --- Data records ---

class JobRecord(BaseModel):
    title: str
    company: str
    url: str
    location: str = ""
    salary: str = ""
    source: str = ""
    ats_type: str = "Other"
    summary: str = ""


class ATSResult(BaseModel):
    status: str  # "Applied" or "Failed"
    error: str = ""


class EmailPayload(BaseModel):
    to_email: str
    to_name: str
    company: str
    subject: str
    body: str
    post_url: str = ""
