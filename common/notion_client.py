"""Notion API wrapper for the Job Applications database."""

import os
from datetime import datetime, timedelta, timezone

from notion_client import AsyncClient

from common.logger import get_logger
from common.schemas import JobRecord

logger = get_logger("notion")


class NotionJobsDB:
    def __init__(self, token: str | None = None, database_id: str | None = None):
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self.client = AsyncClient(auth=self.token)

    async def create_job_record(
        self,
        job: JobRecord,
        status: str = "Queued",
        follow_up_days: int | None = None,
    ) -> str:
        """Create a new job record in Notion. Returns the page ID."""
        properties: dict = {
            "Company": {"title": [{"text": {"content": job.company}}]},
            "Role": {"rich_text": [{"text": {"content": job.title}}]},
            "URL": {"url": job.url},
            "Source": {"select": {"name": job.source}},
            "Status": {"select": {"name": status}},
            "ATS Type": {"select": {"name": job.ats_type}},
        }

        if job.summary:
            properties["Summary"] = {
                "rich_text": [{"text": {"content": job.summary[:2000]}}]
            }

        if follow_up_days:
            follow_up = datetime.now(timezone.utc) + timedelta(days=follow_up_days)
            properties["Follow-up Date"] = {
                "date": {"start": follow_up.date().isoformat()}
            }

        page = await self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
        )
        page_id = page["id"]
        logger.info(f"Created Notion record: {job.company} - {job.title}", extra={"data": {"page_id": page_id}})
        return page_id

    async def update_status(
        self, page_id: str, status: str, error: str = ""
    ) -> None:
        """Update the status of a job record."""
        properties: dict = {
            "Status": {"select": {"name": status}},
        }
        if error:
            properties["Error"] = {
                "rich_text": [{"text": {"content": error[:2000]}}]
            }
        await self.client.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Updated Notion status: {page_id} → {status}")

    async def query_by_url(self, url: str) -> list[dict]:
        """Check if a job URL already exists in the database (for dedup)."""
        response = await self.client.databases.query(
            database_id=self.database_id,
            filter={"property": "URL", "url": {"equals": url}},
        )
        return response.get("results", [])

    async def query_follow_ups(self) -> list[dict]:
        """Get records where follow-up date is today or past and status is still Emailed."""
        today = datetime.now(timezone.utc).date().isoformat()
        response = await self.client.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {"property": "Status", "select": {"equals": "Emailed"}},
                    {
                        "property": "Follow-up Date",
                        "date": {"on_or_before": today},
                    },
                ]
            },
        )
        return response.get("results", [])
