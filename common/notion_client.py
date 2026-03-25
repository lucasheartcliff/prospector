"""Notion API wrapper for the Job Applications database.

Uses httpx directly instead of the third-party notion-client package.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from common.logger import get_logger
from common.schemas import JobRecord

logger = get_logger("notion")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionJobsDB:
    def __init__(self, token: str | None = None, database_id: str | None = None):
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self._http = httpx.AsyncClient(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Make an authenticated request to the Notion API."""
        resp = await self._http.request(method, path, **kwargs)
        if resp.status_code >= 400:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            msg = body.get("message", resp.text[:200])
            logger.error(f"Notion API {method} {path} → {resp.status_code}: {msg}")
            resp.raise_for_status()
        return resp.json()

    # ── Pages ────────────────────────────────────

    async def create_page(self, parent: dict, properties: dict, **kwargs: Any) -> dict:
        """Create a Notion page."""
        payload: dict[str, Any] = {"parent": parent, "properties": properties, **kwargs}
        return await self._request("POST", "/pages", json=payload)

    async def retrieve_page(self, page_id: str) -> dict:
        """Retrieve a Notion page by ID."""
        return await self._request("GET", f"/pages/{page_id}")

    async def update_page(self, page_id: str, properties: dict) -> dict:
        """Update a Notion page's properties."""
        return await self._request("PATCH", f"/pages/{page_id}", json={"properties": properties})

    # ── Databases ────────────────────────────────

    async def create_database(self, parent: dict, title: list, properties: dict, **kwargs: Any) -> dict:
        """Create a Notion database."""
        payload: dict[str, Any] = {
            "parent": parent,
            "title": title,
            "properties": properties,
            **kwargs,
        }
        return await self._request("POST", "/databases", json=payload)

    async def retrieve_database(self, database_id: str) -> dict:
        """Retrieve a Notion database by ID."""
        return await self._request("GET", f"/databases/{database_id}")

    async def query_database(self, database_id: str, filter: dict | None = None, sorts: list | None = None) -> dict:
        """Query a Notion database with optional filter and sorts."""
        payload: dict[str, Any] = {}
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
        return await self._request("POST", f"/databases/{database_id}/query", json=payload)

    # ── Search ───────────────────────────────────

    async def search(self, query: str = "", filter: dict | None = None) -> dict:
        """Search across the workspace."""
        payload: dict[str, Any] = {}
        if query:
            payload["query"] = query
        if filter:
            payload["filter"] = filter
        return await self._request("POST", "/search", json=payload)

    # ── Job-specific methods ─────────────────────

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

        page = await self.create_page(
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
        await self.update_page(page_id, properties)
        logger.info(f"Updated Notion status: {page_id} → {status}")

    async def query_by_url(self, url: str) -> list[dict]:
        """Check if a job URL already exists in the database (for dedup)."""
        response = await self.query_database(
            database_id=self.database_id,
            filter={"property": "URL", "url": {"equals": url}},
        )
        return response.get("results", [])

    async def query_follow_ups(self) -> list[dict]:
        """Get records where follow-up date is today or past and status is still Emailed."""
        today = datetime.now(timezone.utc).date().isoformat()
        response = await self.query_database(
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
