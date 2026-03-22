"""FastAPI server exposing ATS and outreach endpoints for n8n integration."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ats.greenhouse import GreenhouseBot
from ats.lever import LeverBot
from ats.workday import WorkdayBot
from common.constants import Status
from common.discord import notify_error, notify_success
from common.logger import get_logger
from common.notion_client import NotionJobsDB
from common.schemas import ATSResult

logger = get_logger("server")

app = FastAPI(title="Prospector", version="0.1.0")
notion = NotionJobsDB()

RESUME_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "resume.pdf")

_BOTS = {
    "Greenhouse": GreenhouseBot,
    "Lever": LeverBot,
    "Workday": WorkdayBot,
}


# --- Request/Response models ---

class ApplyRequest(BaseModel):
    url: str
    ats_type: str
    notion_page_id: str


class FindEmailRequest(BaseModel):
    linkedin_profile_url: str
    company_domain: str
    first_name: str
    last_name: str


class GenerateEmailRequest(BaseModel):
    author_name: str
    company: str
    post_content: str


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/apply")
async def apply_to_job(request: ApplyRequest) -> ATSResult:
    """Apply to a job via ATS bot. Called by n8n."""
    bot_class = _BOTS.get(request.ats_type)
    if not bot_class:
        raise HTTPException(400, f"Unsupported ATS type: {request.ats_type}")

    resume = RESUME_PATH
    if not Path(resume).exists():
        raise HTTPException(500, "resume.pdf not found in assets/")

    bot = bot_class()
    result = await bot.apply(request.url, resume)

    # Update Notion
    status = result.status if result.status in (Status.APPLIED, Status.MANUAL_REQUIRED) else Status.FAILED
    await notion.update_status(request.notion_page_id, status, result.error)

    # Discord notification
    if result.status == Status.FAILED:
        await notify_error(f"ATS apply failed: {request.url}", result.error)
    else:
        await notify_success("ATS Application", f"Applied to {request.url} via {request.ats_type}")

    return result


@app.post("/find-email")
async def find_email(request: FindEmailRequest) -> dict:
    """Find email for a LinkedIn profile. Called by n8n."""
    from outreach.email_finder import find_email as _find_email

    result = await _find_email(
        linkedin_profile_url=request.linkedin_profile_url,
        company_domain=request.company_domain,
        first_name=request.first_name,
        last_name=request.last_name,
    )
    return result


@app.post("/generate-email")
async def generate_email(request: GenerateEmailRequest) -> dict:
    """Generate a personalized cold email. Called by n8n."""
    from outreach.email_generator import generate as _generate

    result = _generate(
        author_name=request.author_name,
        company=request.company,
        post_content=request.post_content,
    )
    return result


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVER_PORT", "8100"))
    uvicorn.run(app, host="127.0.0.1", port=port)
