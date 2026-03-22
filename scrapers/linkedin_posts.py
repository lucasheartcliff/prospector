"""LinkedIn post scraper — finds hiring signals in recent posts."""

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

import httpx
from playwright.async_api import async_playwright

from common.config import load_config
from common.logger import get_logger

logger = get_logger("linkedin_posts")


async def scrape_posts(
    keywords: list[str] | None = None,
    max_posts: int = 100,
    dry_run: bool = False,
) -> list[dict]:
    """Scrape LinkedIn posts matching hiring keywords from the last 48 hours."""
    config = load_config()
    search_keywords = keywords or [
        "hiring senior backend",
        "looking for java developer",
        "hiring full stack engineer",
        "looking for senior engineer",
    ]

    max_age = datetime.now(timezone.utc) - timedelta(hours=config.limits.post_max_age_hours)
    all_posts: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
        )

        # LinkedIn requires authentication — load cookies from saved session
        # Users must export cookies from their browser and save to config/linkedin_cookies.json
        try:
            cookies_path = config_dir() / "linkedin_cookies.json"
            with open(cookies_path) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
        except FileNotFoundError:
            logger.warning("No linkedin_cookies.json found — LinkedIn will likely block unauthenticated scraping")

        page = await context.new_page()

        for keyword in search_keywords:
            if len(all_posts) >= max_posts:
                break

            logger.info(f"Searching LinkedIn posts: '{keyword}'")
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={keyword}&sortBy=%22date_posted%22"

            try:
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                logger.error(f"Failed to load search results for '{keyword}': {e}")
                continue

            # Scroll to load more posts
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(random.uniform(2, 5))

            # Extract post data
            post_elements = await page.locator(".feed-shared-update-v2").all()

            for element in post_elements:
                if len(all_posts) >= max_posts:
                    break

                try:
                    # Extract author info
                    author_el = element.locator(".update-components-actor__name").first
                    author_name = await author_el.inner_text() if await author_el.count() > 0 else ""

                    profile_link = element.locator("a.update-components-actor__container-link").first
                    profile_url = await profile_link.get_attribute("href") if await profile_link.count() > 0 else ""

                    # Extract company
                    subtitle_el = element.locator(".update-components-actor__description").first
                    company = await subtitle_el.inner_text() if await subtitle_el.count() > 0 else ""

                    # Extract post content
                    content_el = element.locator(".feed-shared-update-v2__description").first
                    content = await content_el.inner_text() if await content_el.count() > 0 else ""

                    # Extract post URL
                    post_link = element.locator("a[href*='/feed/update/']").first
                    post_url = await post_link.get_attribute("href") if await post_link.count() > 0 else ""

                    if author_name and content:
                        post_data = {
                            "post_url": post_url,
                            "author_name": author_name.strip(),
                            "author_profile_url": profile_url,
                            "company": company.strip(),
                            "content": content.strip()[:500],
                            "keyword": keyword,
                        }
                        all_posts.append(post_data)
                        logger.info(f"Found post by {author_name.strip()} at {company.strip()}")

                except Exception as e:
                    logger.error(f"Failed to extract post data: {e}")
                    continue

            # Rate limiting between searches
            await asyncio.sleep(random.uniform(3, 8))

        await browser.close()

    logger.info(f"Scraped {len(all_posts)} posts across {len(search_keywords)} keyword searches")

    if dry_run:
        for post in all_posts:
            print(json.dumps(post, indent=2))
        return all_posts

    return all_posts


def config_dir():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "config"


async def post_to_n8n(posts: list[dict]) -> None:
    """POST scraped posts to the n8n webhook."""
    config = load_config()
    webhook_url = f"{config.n8n_webhook_url}/posts"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(webhook_url, json=posts)
        resp.raise_for_status()

    logger.info(f"Posted {len(posts)} posts to n8n webhook")


async def main(keywords: list[str] | None = None, dry_run: bool = False) -> None:
    posts = await scrape_posts(keywords=keywords, dry_run=dry_run)
    if not dry_run and posts:
        await post_to_n8n(posts)
    elif not posts:
        logger.info("No hiring posts found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape LinkedIn posts for hiring signals")
    parser.add_argument("--keywords", nargs="+", help="Override search keywords")
    parser.add_argument("--dry-run", action="store_true", help="Print results without posting to n8n")
    args = parser.parse_args()
    asyncio.run(main(keywords=args.keywords, dry_run=args.dry_run))
