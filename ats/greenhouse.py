"""Greenhouse ATS form automation."""

import argparse
import asyncio

from playwright.async_api import Page

from ats.base import ATSBot, logger
from common.schemas import ATSResult


class GreenhouseBot(ATSBot):
    name = "greenhouse"

    async def _fill_and_submit(self, page: Page, url: str, resume_path: str) -> ATSResult:
        await page.goto(url, wait_until="networkidle")

        personal = self.answers.personal

        # Fill personal information
        await self._fill_field(page, "#first_name", personal.full_name.split()[0])
        await self._fill_field(page, "#last_name", " ".join(personal.full_name.split()[1:]))
        await self._fill_field(page, "#email", personal.email)
        await self._fill_field(page, "#phone", personal.phone)

        # Upload resume
        file_input = page.locator("input[type='file']").first
        if await file_input.count() > 0:
            await file_input.set_input_files(resume_path)
            logger.info("[greenhouse] Resume uploaded")

        # Fill LinkedIn URL if field exists
        linkedin_field = page.locator("[id*='linkedin'], [name*='linkedin'], [placeholder*='LinkedIn']").first
        if await linkedin_field.count() > 0:
            await linkedin_field.fill(personal.linkedin_url)

        # Handle multi-step forms
        while True:
            next_btn = page.locator("button:has-text('Next'), button:has-text('Continue')").first
            if await next_btn.count() > 0 and await next_btn.is_visible():
                await next_btn.click()
                await page.wait_for_load_state("networkidle")
            else:
                break

        # Submit
        submit_btn = page.locator(
            "button[type='submit']:has-text('Submit'), "
            "input[type='submit'], "
            "button:has-text('Submit Application')"
        ).first

        if await submit_btn.count() > 0:
            await submit_btn.click()
            await page.wait_for_load_state("networkidle")

            # Check for confirmation
            confirmation = page.locator(
                "text=Thank you, text=Application submitted, text=received your application"
            ).first
            if await confirmation.count() > 0:
                return ATSResult(status="Applied")

            return ATSResult(status="Applied")

        return ATSResult(status="Failed", error="Submit button not found")

    async def _fill_field(self, page: Page, selector: str, value: str) -> None:
        field = page.locator(selector).first
        if await field.count() > 0 and await field.is_visible():
            await field.fill(value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply to a Greenhouse job")
    parser.add_argument("--url", required=True, help="Greenhouse job URL")
    parser.add_argument("--resume", default="assets/resume.pdf", help="Path to resume PDF")
    args = parser.parse_args()

    bot = GreenhouseBot()
    result = asyncio.run(bot.apply(args.url, args.resume))
    print(f"Result: {result.status}" + (f" — {result.error}" if result.error else ""))
