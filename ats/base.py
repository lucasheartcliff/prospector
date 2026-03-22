"""Abstract base class for ATS form automation bots."""

import asyncio
import os
import random
from abc import ABC, abstractmethod

from playwright.async_api import Page, async_playwright

from common.config import load_answers
from common.logger import get_logger
from common.schemas import ATSResult, AnswersConfig

logger = get_logger("ats")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


class ATSBot(ABC):
    """Base class for ATS form automation."""

    name: str = "base"
    timeout_ms: int = 90_000
    max_retries: int = 2

    def __init__(self, answers: AnswersConfig | None = None):
        self.answers = answers or load_answers()

    async def apply(self, url: str, resume_path: str) -> ATSResult:
        """Launch browser, fill form, submit. Retries on failure."""
        headless = not os.getenv("DEBUG", "").lower() in ("true", "1")
        user_agent = random.choice(USER_AGENTS)

        for attempt in range(self.max_retries + 1):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=headless)
                    context = await browser.new_context(user_agent=user_agent)
                    context.set_default_timeout(self.timeout_ms)
                    page = await context.new_page()

                    logger.info(f"[{self.name}] Attempt {attempt + 1}: {url}")
                    result = await self._fill_and_submit(page, url, resume_path)
                    await browser.close()

                    logger.info(f"[{self.name}] Result: {result.status}")
                    return result

            except Exception as e:
                logger.error(f"[{self.name}] Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    delay = (2**attempt) * 5 + random.uniform(0, 3)
                    logger.info(f"[{self.name}] Retrying in {delay:.0f}s...")
                    await asyncio.sleep(delay)
                else:
                    return ATSResult(status="Failed", error=str(e))

        return ATSResult(status="Failed", error="Max retries exceeded")

    @abstractmethod
    async def _fill_and_submit(self, page: Page, url: str, resume_path: str) -> ATSResult:
        """Implement the actual form filling and submission logic."""
        ...
