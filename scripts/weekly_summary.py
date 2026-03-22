"""Weekly summary report — queries Notion stats and posts to Discord."""

import asyncio
from collections import Counter

from common.discord import notify
from common.logger import get_logger
from common.notion_client import NotionJobsDB

logger = get_logger("weekly_summary")


async def generate_summary() -> str:
    """Query Notion and generate a weekly summary."""
    notion = NotionJobsDB()

    # Query all records from the last 7 days
    from datetime import datetime, timedelta, timezone

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()

    response = await notion.client.databases.query(
        database_id=notion.database_id,
        filter={
            "property": "Created",
            "created_time": {"on_or_after": week_ago},
        },
    )

    records = response.get("results", [])

    if not records:
        return "No activity this week."

    # Count by status and source
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for record in records:
        props = record.get("properties", {})
        status = props.get("Status", {}).get("select", {}).get("name", "Unknown")
        source = props.get("Source", {}).get("select", {}).get("name", "Unknown")
        status_counts[status] += 1
        source_counts[source] += 1

    lines = [
        "**Weekly Pipeline Summary**",
        f"Total records: {len(records)}",
        "",
        "**By Status:**",
    ]
    for status, count in status_counts.most_common():
        lines.append(f"  {status}: {count}")

    lines.append("")
    lines.append("**By Source:**")
    for source, count in source_counts.most_common():
        lines.append(f"  {source}: {count}")

    return "\n".join(lines)


async def main() -> None:
    summary = await generate_summary()
    logger.info(f"Weekly summary:\n{summary}")
    await notify(summary)


if __name__ == "__main__":
    asyncio.run(main())
