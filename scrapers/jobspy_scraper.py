"""Multi-board job listing aggregation using JobSpy."""

import argparse
import asyncio
import json
import sys

import httpx
from jobspy import scrape_jobs

from common.config import load_blacklist, load_config
from common.constants import detect_ats_type
from common.discord import notify_success
from common.logger import get_logger
from common.schemas import JobRecord

logger = get_logger("jobspy_scraper")


def scrape(dry_run: bool = False, titles: list[str] | None = None) -> list[JobRecord]:
    """Scrape jobs from all configured boards and return deduplicated records."""
    config = load_config()
    blacklist = load_blacklist()
    search_titles = titles or config.search.titles
    all_jobs: list[JobRecord] = []
    seen_urls: set[str] = set()

    for title in search_titles:
        for location in config.search.locations:
            logger.info(f"Scraping: '{title}' in '{location}'")
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"],
                    search_term=title,
                    location=location,
                    results_wanted=50,
                    hours_old=24,
                )
            except Exception as e:
                logger.error(f"Scrape failed for '{title}' / '{location}': {e}")
                continue

            for _, row in df.iterrows():
                url = str(row.get("job_url", ""))
                company = str(row.get("company", ""))

                if not url or url in seen_urls:
                    continue
                if company.lower() in {c.lower() for c in blacklist.companies}:
                    logger.info(f"Skipping blacklisted company: {company}")
                    continue

                seen_urls.add(url)
                job = JobRecord(
                    title=str(row.get("title", "")),
                    company=company,
                    url=url,
                    location=str(row.get("location", "")),
                    salary=str(row.get("salary", "")),
                    source="JobSpy",
                    ats_type=detect_ats_type(url),
                )
                all_jobs.append(job)

    logger.info(f"Found {len(all_jobs)} unique jobs across {len(search_titles)} titles")

    if dry_run:
        for job in all_jobs:
            print(json.dumps(job.model_dump(), indent=2))
        return all_jobs

    return all_jobs


async def post_to_n8n(jobs: list[JobRecord]) -> None:
    """POST job records to the n8n webhook for processing."""
    config = load_config()
    webhook_url = f"{config.n8n_webhook_url}/jobs"

    payload = [job.model_dump() for job in jobs]
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()

    logger.info(f"Posted {len(jobs)} jobs to n8n webhook")
    await notify_success(
        "JobSpy Scraper",
        f"Found and posted {len(jobs)} new jobs to pipeline.",
    )


async def main(dry_run: bool = False, titles: list[str] | None = None) -> None:
    jobs = scrape(dry_run=dry_run, titles=titles)
    if not dry_run and jobs:
        await post_to_n8n(jobs)
    elif not jobs:
        logger.info("No new jobs found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape jobs from multiple boards")
    parser.add_argument("--dry-run", action="store_true", help="Print results without posting to n8n")
    parser.add_argument("--titles", nargs="+", help="Override search titles")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, titles=args.titles))
