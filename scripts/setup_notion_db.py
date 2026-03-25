#!/usr/bin/env python3
"""Create the Prospector 'Job Applications' database in Notion.

This script creates a fully configured database under a parent page,
with all required properties, select options, and default views.

Usage:
    python scripts/setup_notion_db.py
    python scripts/setup_notion_db.py --parent-page-id <PAGE_ID>
    python scripts/setup_notion_db.py --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

# ANSI colors
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"

# ──────────────────────────────────────────────
# Database schema definition
# ──────────────────────────────────────────────

STATUS_OPTIONS = [
    {"name": "Queued", "color": "default"},
    {"name": "Applied", "color": "blue"},
    {"name": "Emailed", "color": "purple"},
    {"name": "Interview", "color": "yellow"},
    {"name": "Offer", "color": "green"},
    {"name": "Rejected", "color": "red"},
    {"name": "Failed", "color": "orange"},
    {"name": "Manual Required", "color": "pink"},
]

SOURCE_OPTIONS = [
    {"name": "JobSpy", "color": "blue"},
    {"name": "LinkedIn Easy Apply", "color": "green"},
    {"name": "Post Outreach", "color": "purple"},
    {"name": "Manual", "color": "default"},
]

ATS_TYPE_OPTIONS = [
    {"name": "Greenhouse", "color": "green"},
    {"name": "Lever", "color": "blue"},
    {"name": "Workday", "color": "orange"},
    {"name": "Other", "color": "default"},
    {"name": "Easy Apply", "color": "purple"},
]

DATABASE_PROPERTIES = {
    # "Company" is the title property — defined as part of the database creation
    "Role": {
        "rich_text": {},
    },
    "URL": {
        "url": {},
    },
    "Source": {
        "select": {
            "options": SOURCE_OPTIONS,
        },
    },
    "Status": {
        "select": {
            "options": STATUS_OPTIONS,
        },
    },
    "ATS Type": {
        "select": {
            "options": ATS_TYPE_OPTIONS,
        },
    },
    "Summary": {
        "rich_text": {},
    },
    "Follow-up Date": {
        "date": {},
    },
    "Contact Email": {
        "email": {},
    },
    "Error": {
        "rich_text": {},
    },
    "Applied Date": {
        "date": {},
    },
    "Job Location": {
        "rich_text": {},
    },
    "Salary": {
        "rich_text": {},
    },
    "Notes": {
        "rich_text": {},
    },
}

DATABASE_ICON = {"type": "emoji", "emoji": "⛏️"}

DATABASE_DESCRIPTION = [
    {
        "type": "text",
        "text": {
            "content": "Prospector job application pipeline — auto-populated by scrapers, ATS bots, and outreach modules.",
        },
    }
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def success(msg: str):
    print(f"  {GREEN}✔{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def error(msg: str):
    print(f"  {RED}✖{RESET} {msg}")


def info(msg: str):
    print(f"  {DIM}→{RESET} {msg}")


def update_env_file(key: str, value: str):
    """Update or append a key in the .env file."""
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    content = env_path.read_text()
    lines = content.splitlines()
    found = False

    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break

    if not found:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n")


def _extract_page_title(page: dict) -> str:
    """Extract plain text title from a Notion page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


# ──────────────────────────────────────────────
# Parent page discovery
# ──────────────────────────────────────────────

async def find_or_create_parent(notion, parent_page_id: str | None) -> dict:
    """Resolve the parent for the database.

    If parent_page_id is given, validate it exists.
    Otherwise, search for a 'Prospector' page or offer to create one.
    """
    # Explicit parent provided
    if parent_page_id:
        try:
            page = await notion.retrieve_page(parent_page_id)
            title = _extract_page_title(page)
            success(f"Using parent page: \"{title}\" ({parent_page_id[:8]}...)")
            return {"type": "page_id", "page_id": parent_page_id}
        except Exception as e:
            error(f"Could not access page {parent_page_id}: {e}")
            sys.exit(1)

    # Search for existing 'Prospector' page
    info("Searching for a 'Prospector' page in your workspace...")
    try:
        results = await notion.search(
            query="Prospector",
            filter={"property": "object", "value": "page"},
        )

        pages = results.get("results", [])
        prospector_pages = [
            p for p in pages
            if "prospector" in _extract_page_title(p).lower()
        ]

        if prospector_pages:
            page = prospector_pages[0]
            title = _extract_page_title(page)
            page_id = page["id"]
            print()
            info(f"Found existing page: \"{title}\"")
            use_it = input(f"  Use this as the parent? [Y/n]: ").strip().lower()
            if use_it in ("", "y", "yes"):
                success(f"Using parent page: \"{title}\"")
                return {"type": "page_id", "page_id": page_id}

    except Exception:
        pass

    # Create a new parent page
    print()
    info("No suitable parent page found.")
    print()
    info("The database needs a parent page in Notion.")
    info("Options:")
    print(f"    {BOLD}1{RESET} — Create a new 'Prospector' page (recommended)")
    print(f"    {BOLD}2{RESET} — Enter a page ID manually")
    print()

    choice = input("  Choose [1]: ").strip() or "1"

    if choice == "2":
        page_id = input("  Enter parent page ID: ").strip()
        if not page_id:
            error("No page ID provided")
            sys.exit(1)
        return {"type": "page_id", "page_id": page_id}

    # Create new page at workspace root
    info("Creating 'Prospector' page...")
    try:
        new_page = await notion.create_page(
            parent={"type": "workspace", "workspace": True},
            properties={
                "title": [{"text": {"content": "Prospector"}}],
            },
            icon=DATABASE_ICON,
        )
        page_id = new_page["id"]
        success(f"Created parent page: \"Prospector\" ({page_id[:8]}...)")
        return {"type": "page_id", "page_id": page_id}
    except Exception as e:
        error(f"Could not create page at workspace level: {e}")
        info("Your integration may not have workspace-level access.")
        info("Try creating a page manually in Notion, share it with your integration,")
        info("then re-run with: python scripts/setup_notion_db.py --parent-page-id <PAGE_ID>")
        sys.exit(1)


# ──────────────────────────────────────────────
# Database creation
# ──────────────────────────────────────────────

async def check_existing_database(notion) -> str | None:
    """Check if a 'Job Applications' database already exists."""
    try:
        results = await notion.search(
            query="Job Applications",
            filter={"property": "object", "value": "database"},
        )
        for db in results.get("results", []):
            title_parts = db.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts)
            if title == "Job Applications":
                return db["id"]
    except Exception:
        pass
    return None


async def create_database_record(notion, parent: dict, dry_run: bool = False) -> str:
    """Create the Job Applications database with all properties and views."""

    # Build the full properties dict including the title property
    properties = {
        "Company": {"title": {}},
        **DATABASE_PROPERTIES,
    }

    payload = {
        "parent": parent,
        "title": [{"type": "text", "text": {"content": "Job Applications"}}],
        "description": DATABASE_DESCRIPTION,
        "icon": DATABASE_ICON,
        "properties": properties,
        "is_inline": False,
    }

    if dry_run:
        print(f"\n{DIM}  Dry run — would create database with this payload:{RESET}\n")
        print(json.dumps(payload, indent=2))
        return "dry-run-id"

    info("Creating 'Job Applications' database...")
    db = await notion.create_database(**payload)
    db_id = db["id"]
    success(f"Database created: {db_id}")

    return db_id


async def seed_board_view_example(notion, db_id: str):
    """Create a sample record so the database isn't empty."""
    info("Creating sample record...")
    try:
        await notion.create_page(
            parent={"database_id": db_id},
            properties={
                "Company": {"title": [{"text": {"content": "Example Corp (delete me)"}}]},
                "Role": {"rich_text": [{"text": {"content": "Senior Software Engineer"}}]},
                "URL": {"url": "https://example.com/jobs/123"},
                "Source": {"select": {"name": "Manual"}},
                "Status": {"select": {"name": "Queued"}},
                "ATS Type": {"select": {"name": "Other"}},
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "This is a sample record created by the setup script. You can delete it."
                            }
                        }
                    ]
                },
            },
        )
        success("Sample record created (you can delete it from Notion)")
    except Exception as e:
        warn(f"Could not create sample record: {e}")


# ──────────────────────────────────────────────
# Views guidance
# ──────────────────────────────────────────────

def print_views_guide():
    """Print instructions for creating Notion views (can't be done via API)."""
    print(f"""
  {BOLD}Recommended views{RESET} {DIM}(create these manually in Notion):{RESET}

  {CYAN}1. Board View — "Pipeline"{RESET}
     • Click "+ Add a view" → Board
     • Group by: {BOLD}Status{RESET}
     • This gives you a Kanban board of your application pipeline

  {CYAN}2. Table View — "Recent Applications"{RESET}
     • Click "+ Add a view" → Table
     • Filter: Created is within the past week
     • Sort: Created, Descending
     • Shows what was applied in the last 7 days

  {CYAN}3. Table View — "Follow-ups Due"{RESET}
     • Click "+ Add a view" → Table
     • Filter: Status equals "Emailed" AND Follow-up Date is on or before today
     • Sort: Follow-up Date, Ascending
     • Shows outreach that needs follow-up

  {CYAN}4. Table View — "By Source"{RESET}
     • Click "+ Add a view" → Table
     • Group by: {BOLD}Source{RESET}
     • See volume breakdown by channel
""")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

async def run(parent_page_id: str | None = None, dry_run: bool = False, no_sample: bool = False):
    print(f"""
{CYAN}{BOLD}  ⛏️  Prospector — Notion Database Setup{RESET}
{DIM}  Creates the Job Applications database with all properties{RESET}
{DIM}  ────────────────────────────────────────────────────────{RESET}
""")

    # Validate token
    token = os.getenv("NOTION_TOKEN", "")
    if not token:
        error("NOTION_TOKEN not found in environment or .env file")
        info("Run 'python scripts/init.py' first, or set NOTION_TOKEN in .env")
        sys.exit(1)

    # Use the internal Notion client
    sys.path.insert(0, str(PROJECT_DIR))
    from common.notion_client import NotionJobsDB
    notion = NotionJobsDB(token=token)

    # Check for existing database
    existing_id = os.getenv("NOTION_DATABASE_ID", "")
    if existing_id:
        info(f"NOTION_DATABASE_ID is already set: {existing_id[:8]}...")
        try:
            db = await notion.retrieve_database(existing_id)
            title_parts = db.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts)
            success(f"Database exists and is accessible: \"{title}\"")
            print()
            recreate = input("  Create a new database anyway? [y/N]: ").strip().lower()
            if recreate not in ("y", "yes"):
                info("Keeping existing database")
                print_views_guide()
                return
        except Exception:
            warn("Existing database ID is not accessible — will create a new one")

    # Also check by name
    found_id = await check_existing_database(notion)
    if found_id and found_id != existing_id:
        info(f"Found existing 'Job Applications' database: {found_id[:8]}...")
        use_existing = input("  Use this database instead of creating a new one? [Y/n]: ").strip().lower()
        if use_existing in ("", "y", "yes"):
            update_env_file("NOTION_DATABASE_ID", found_id)
            success(f"NOTION_DATABASE_ID updated in .env: {found_id[:8]}...")
            print_views_guide()
            return

    # Find or create parent page
    parent = await find_or_create_parent(notion, parent_page_id)

    # Create the database
    db_id = await create_database_record(notion, parent, dry_run=dry_run)

    if not dry_run:
        # Save database ID to .env
        update_env_file("NOTION_DATABASE_ID", db_id)
        success(f"NOTION_DATABASE_ID saved to .env")

        # Create sample record
        if not no_sample:
            await seed_board_view_example(notion, db_id)

        # Print view setup guide
        print_views_guide()

        # Final summary
        print(f"  {GREEN}{BOLD}Database is ready!{RESET}")
        print(f"  {DIM}Database ID: {db_id}{RESET}")
        print(f"  {DIM}Open Notion to see it and set up the views above.{RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Create the Prospector Job Applications database in Notion",
    )
    parser.add_argument(
        "--parent-page-id",
        help="Notion page ID to use as parent for the database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the database payload without creating anything",
    )
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Skip creating the sample record",
    )
    args = parser.parse_args()
    asyncio.run(run(
        parent_page_id=args.parent_page_id,
        dry_run=args.dry_run,
        no_sample=args.no_sample,
    ))


if __name__ == "__main__":
    main()
