"""LLM-powered personalized cold email generator."""

import argparse
import json
from pathlib import Path

from common.llm_client import LLMClient
from common.logger import get_logger

logger = get_logger("email_generator")

RESUME_JSON_PATH = Path(__file__).resolve().parent.parent / "assets" / "resume.json"


def _load_resume() -> str:
    """Load resume.json as string."""
    if RESUME_JSON_PATH.exists():
        return RESUME_JSON_PATH.read_text()
    logger.warning("resume.json not found, using empty resume")
    return "{}"


def generate(
    author_name: str,
    company: str,
    post_content: str,
    resume_json: str | None = None,
) -> dict:
    """Generate a personalized cold email.

    Returns dict with keys: subject, body
    """
    resume = resume_json or _load_resume()
    client = LLMClient()

    subject, body = client.generate_email(
        author_name=author_name,
        company=company,
        post_content=post_content,
        resume_json=resume,
    )

    logger.info(f"Generated email for {author_name} at {company}")
    return {"subject": subject, "body": body}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a personalized cold email")
    parser.add_argument("--author", required=True, help="Author name")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--post-content", required=True, help="LinkedIn post content")
    parser.add_argument("--dry-run", action="store_true", help="Print email without sending")
    args = parser.parse_args()

    result = generate(
        author_name=args.author,
        company=args.company,
        post_content=args.post_content,
    )

    print(f"\nSubject: {result['subject']}")
    print(f"\n{result['body']}")
