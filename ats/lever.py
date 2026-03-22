"""Lever ATS form automation."""

import argparse
import asyncio

from playwright.async_api import Page

from ats.base import ATSBot, logger
from common.schemas import ATSResult


class LeverBot(ATSBot):
    name = "lever"

    async def _fill_and_submit(self, page: Page, url: str, resume_path: str) -> ATSResult:
        # Lever application pages are at /apply suffix
        apply_url = url if url.endswith("/apply") else f"{url.rstrip('/')}/apply"
        await page.goto(apply_url, wait_until="networkidle")

        personal = self.answers.personal

        # Fill personal information
        await self._fill_field(page, "input[name='name']", personal.full_name)
        await self._fill_field(page, "input[name='email']", personal.email)
        await self._fill_field(page, "input[name='phone']", personal.phone)
        await self._fill_field(page, "input[name='org']", self.answers.work.current_company)

        # Fill LinkedIn URL
        linkedin_field = page.locator("input[name='urls[LinkedIn]'], input[placeholder*='LinkedIn']").first
        if await linkedin_field.count() > 0:
            await linkedin_field.fill(personal.linkedin_url)

        # Fill GitHub URL
        github_field = page.locator("input[name='urls[GitHub]'], input[placeholder*='GitHub']").first
        if await github_field.count() > 0:
            await github_field.fill(personal.github_url)

        # Upload resume
        file_input = page.locator("input[type='file']").first
        if await file_input.count() > 0:
            await file_input.set_input_files(resume_path)
            logger.info("[lever] Resume uploaded")

        # Fill "Additional Information" textarea if present
        additional = page.locator("textarea[name='comments']").first
        if await additional.count() > 0:
            await additional.fill(self.answers.answers.cover_letter_default[:1000])

        # Submit
        submit_btn = page.locator(
            "button[type='submit']:has-text('Submit'), "
            "button:has-text('Submit application'), "
            "a.postings-btn-submit"
        ).first

        if await submit_btn.count() > 0:
            await submit_btn.click()
            await page.wait_for_load_state("networkidle")

            confirmation = page.locator(
                "text=Application submitted, text=Thank you, text=your application has been"
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
    parser = argparse.ArgumentParser(description="Apply to a Lever job")
    parser.add_argument("--url", required=True, help="Lever job URL")
    parser.add_argument("--resume", default="assets/resume.pdf", help="Path to resume PDF")
    args = parser.parse_args()

    bot = LeverBot()
    result = asyncio.run(bot.apply(args.url, args.resume))
    print(f"Result: {result.status}" + (f" — {result.error}" if result.error else ""))
