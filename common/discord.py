"""Discord webhook notifications."""

import os

import httpx

from common.logger import get_logger

logger = get_logger("discord")


async def notify(message: str, webhook_url: str | None = None) -> None:
    """Send a plain text message to Discord."""
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        logger.warning("DISCORD_WEBHOOK_URL not set, skipping notification")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"content": message})
        resp.raise_for_status()


async def notify_error(title: str, error: str, webhook_url: str | None = None) -> None:
    """Send an error notification with an embed to Discord."""
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        logger.warning("DISCORD_WEBHOOK_URL not set, skipping notification")
        return

    payload = {
        "embeds": [
            {
                "title": f"❌ {title}",
                "description": error[:2000],
                "color": 0xFF0000,
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


async def notify_success(title: str, description: str, webhook_url: str | None = None) -> None:
    """Send a success notification with an embed to Discord."""
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return

    payload = {
        "embeds": [
            {
                "title": f"✅ {title}",
                "description": description[:2000],
                "color": 0x00FF00,
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
