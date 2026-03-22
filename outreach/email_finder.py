"""Email discovery — LinkedIn profile scraping + Hunter.io fallback."""

import argparse
import asyncio
import os

import httpx

from common.config import load_config
from common.logger import get_logger

logger = get_logger("email_finder")


async def find_email(
    linkedin_profile_url: str,
    company_domain: str,
    first_name: str,
    last_name: str,
) -> dict:
    """Find an email address for a contact.

    Strategy:
    1. Try Hunter.io email finder API
    2. Return result with confidence score

    Returns dict with keys: email, confidence, source, verified
    """
    config = load_config()
    min_confidence = config.limits.hunter_min_confidence

    # Try Hunter.io
    hunter_result = await _hunter_lookup(first_name, last_name, company_domain)
    if hunter_result and hunter_result["confidence"] >= min_confidence:
        logger.info(
            f"Hunter.io found email for {first_name} {last_name}: "
            f"{hunter_result['email']} (confidence: {hunter_result['confidence']}%)"
        )
        return {
            "email": hunter_result["email"],
            "confidence": hunter_result["confidence"],
            "source": "hunter.io",
            "verified": True,
        }

    if hunter_result:
        logger.warning(
            f"Hunter.io result below confidence threshold "
            f"({hunter_result['confidence']}% < {min_confidence}%)"
        )
        return {
            "email": hunter_result["email"],
            "confidence": hunter_result["confidence"],
            "source": "hunter.io",
            "verified": False,
        }

    logger.warning(f"No email found for {first_name} {last_name} at {company_domain}")
    return {"email": "", "confidence": 0, "source": "none", "verified": False}


async def _hunter_lookup(first_name: str, last_name: str, domain: str) -> dict | None:
    """Look up email via Hunter.io API."""
    api_key = os.getenv("HUNTER_API_KEY", "")
    if not api_key:
        logger.warning("HUNTER_API_KEY not set, skipping Hunter.io lookup")
        return None

    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": api_key,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            if data.get("email"):
                return {
                    "email": data["email"],
                    "confidence": data.get("score", 0),
                }
        except Exception as e:
            logger.error(f"Hunter.io lookup failed: {e}")

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find email for a contact")
    parser.add_argument("--profile-url", required=True, help="LinkedIn profile URL")
    parser.add_argument("--company-domain", required=True, help="Company domain")
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    args = parser.parse_args()

    result = asyncio.run(
        find_email(args.profile_url, args.company_domain, args.first_name, args.last_name)
    )
    print(f"Email: {result['email']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Source: {result['source']}")
    print(f"Verified: {result['verified']}")
