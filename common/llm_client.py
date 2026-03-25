"""Multi-provider LLM client with daily rate limiting.

Supports Anthropic Claude, OpenAI GPT, and Google Gemini.
Provider is selected via the LLM_PROVIDER environment variable.
"""

import os
from typing import Literal

from common.config import load_config
from common.logger import get_logger
from common.rate_limiter import RateLimiter

logger = get_logger("llm")
_rate_limiter = RateLimiter()

LLMProvider = Literal["anthropic", "openai", "gemini"]

# Model tiers per provider: (default, cheap)
_MODELS: dict[LLMProvider, dict[str, str]] = {
    "anthropic": {"default": "claude-sonnet-4-20250514", "cheap": "claude-haiku-4-5-20251001"},
    "openai":    {"default": "gpt-4o",                   "cheap": "gpt-4o-mini"},
    "gemini":    {"default": "gemini-2.5-flash",          "cheap": "gemini-2.0-flash-lite"},
}

_API_KEY_ENV: dict[LLMProvider, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def _detect_provider() -> LLMProvider:
    """Detect provider from LLM_PROVIDER env var, defaulting to anthropic."""
    raw = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()
    if raw in _MODELS:
        return raw  # type: ignore[return-value]
    logger.warning(f"Unknown LLM_PROVIDER '{raw}', falling back to anthropic")
    return "anthropic"


class LLMClient:
    """Unified LLM client supporting Anthropic, OpenAI, and Gemini."""

    def __init__(self, provider: LLMProvider | None = None, api_key: str | None = None):
        self.provider: LLMProvider = provider or _detect_provider()
        self.api_key = api_key or os.getenv(_API_KEY_ENV[self.provider], "")
        self._config = load_config()
        self._client = self._init_client()

    def _init_client(self):
        if self.provider == "anthropic":
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.api_key)
        elif self.provider == "gemini":
            from google import genai
            return genai.Client(api_key=self.api_key)

    def _check_limit(self) -> bool:
        return _rate_limiter.can_proceed("llm", self._config.limits.llm_calls_daily)

    def _call(self, system: str, user_message: str, tier: str = "default") -> str:
        """Make an LLM call using the configured provider.

        Args:
            system: System prompt.
            user_message: User message.
            tier: "default" for quality tasks, "cheap" for high-volume/simple tasks.
        """
        if not self._check_limit():
            raise RuntimeError("LLM daily call limit reached")

        model = _MODELS[self.provider][tier]

        if self.provider == "anthropic":
            text = self._call_anthropic(system, user_message, model)
        elif self.provider == "openai":
            text = self._call_openai(system, user_message, model)
        elif self.provider == "gemini":
            text = self._call_gemini(system, user_message, model)

        _rate_limiter.increment("llm")
        return text

    def _call_anthropic(self, system: str, user_message: str, model: str) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def _call_openai(self, system: str, user_message: str, model: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _call_gemini(self, system: str, user_message: str, model: str) -> str:
        response = self._client.models.generate_content(
            model=model,
            contents=user_message,
            config={"system_instruction": system, "max_output_tokens": 1024},
        )
        return response.text

    # ── High-level methods ──────────────────────────

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
        return self._call(system, user_msg, tier="cheap")

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


# Backward-compatible alias
ClaudeClient = LLMClient
