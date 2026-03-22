"""Anthropic Claude API wrapper with daily rate limiting."""

import os

import anthropic

from common.config import load_config
from common.logger import get_logger
from common.rate_limiter import RateLimiter

logger = get_logger("claude")
_rate_limiter = RateLimiter()


class ClaudeClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self._config = load_config()

    def _check_limit(self) -> bool:
        return _rate_limiter.can_proceed("claude", self._config.limits.claude_calls_daily)

    def _call(self, system: str, user_message: str, model: str = "claude-sonnet-4-20250514") -> str:
        if not self._check_limit():
            raise RuntimeError("Claude daily call limit reached")

        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        _rate_limiter.increment("claude")
        return response.content[0].text

    def generate_summary(self, job_title: str, job_description: str, resume_json: str) -> str:
        """Generate a 3-sentence tailored candidate summary for a job."""
        system = (
            "You are a career advisor. Write exactly 3 concise sentences explaining "
            "why this candidate is a strong fit for the role. Reference specific skills "
            "from their resume that match the job requirements."
        )
        user_msg = (
            f"Job Title: {job_title}\n\n"
            f"Job Description:\n{job_description[:3000]}\n\n"
            f"Candidate Resume (JSON):\n{resume_json[:3000]}"
        )
        return self._call(system, user_msg, model="claude-haiku-4-5-20251001")

    def generate_email(
        self, author_name: str, company: str, post_content: str, resume_json: str
    ) -> tuple[str, str]:
        """Generate a personalized cold email. Returns (subject, body)."""
        system = (
            "You write concise cold emails for job seekers. The email must be under "
            "150 words. Reference the specific LinkedIn post. Highlight exactly 2 "
            "relevant skills from the resume. Be professional but personable. "
            "Return the output in this exact format:\n"
            "SUBJECT: <subject line>\n"
            "BODY:\n<email body>"
        )
        user_msg = (
            f"Author: {author_name}\n"
            f"Company: {company}\n\n"
            f"LinkedIn Post:\n{post_content[:2000]}\n\n"
            f"Resume (JSON):\n{resume_json[:3000]}"
        )
        result = self._call(system, user_msg)

        lines = result.strip().split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip() if lines else f"Senior Developer — interested in {company}"
        body = lines[2].replace("BODY:", "").strip() if len(lines) > 2 else result
        return subject, body

    def answer_question(self, question: str, resume_json: str) -> str:
        """Answer a novel application form question using resume context."""
        system = (
            "You are filling out a job application form on behalf of a candidate. "
            "Answer the question concisely and professionally based on their resume. "
            "Keep the answer under 200 words."
        )
        user_msg = f"Question: {question}\n\nResume (JSON):\n{resume_json[:3000]}"
        return self._call(system, user_msg)
