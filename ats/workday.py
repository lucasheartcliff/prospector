"""Workday ATS — stub that flags jobs as Manual Required."""

import argparse
import asyncio

from playwright.async_api import Page

from ats.base import ATSBot, logger
from common.schemas import ATSResult


class WorkdayBot(ATSBot):
    name = "workday"

    async def _fill_and_submit(self, page: Page, url: str, resume_path: str) -> ATSResult:
        logger.warning(f"[workday] Workday automation is unreliable. Flagging as Manual Required: {url}")
        return ATSResult(
            status="Manual Required",
            error="Workday shadow DOM automation not yet supported. Apply manually.",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply to a Workday job (stub)")
    parser.add_argument("--url", required=True, help="Workday job URL")
    args = parser.parse_args()

    bot = WorkdayBot()
    result = asyncio.run(bot.apply(args.url, "assets/resume.pdf"))
    print(f"Result: {result.status} — {result.error}")
