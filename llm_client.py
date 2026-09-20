"""Legacy Agnes client retained for the dictionary-based pipeline.

The active Streamlit application uses :mod:`src.agnes_client` instead. This
module remains for compatibility with the older ``pipeline.py`` interface.
"""

import os
import time

import openai
from openai import OpenAI

AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-3.0-flash"


def is_agnes_configured() -> bool:
    """Return whether the legacy client can read the Agnes credential.

    Returns:
        True when ``AGNESAI_API_KEY`` is non-blank in the process environment.
    """
    return bool(os.environ.get("AGNESAI_API_KEY", "").strip())


def create_llm_client() -> OpenAI:
    """Create the legacy official OpenAI-compatible Agnes client.

    Returns:
        Configured SDK client pointed at the Agnes base URL.

    Raises:
        ValueError: If ``AGNESAI_API_KEY`` is unavailable.

    Note:
        New code should call ``src.agnes_client.chat_completion``.
    """
    api_key = os.environ.get("AGNESAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Required environment variable AGNESAI_API_KEY is unavailable.")
    return OpenAI(api_key=api_key, base_url=AGNES_BASE_URL, timeout=30.0, max_retries=0)


def get_chat_completion(
    messages: list[dict[str, str]], *, temperature: float = 0.2, max_retries: int = 3
) -> str:
    """Run a legacy Agnes chat completion with bounded rate-limit retries.

    Args:
        messages: OpenAI-compatible system and user messages.
        temperature: Sampling temperature for this legacy call.
        max_retries: Total attempts after HTTP 429 responses.

    Returns:
        Completion text, or an empty string when the SDK response has no text.

    Raises:
        RateLimitError: If every configured attempt is rate-limited.
        RuntimeError: If no completion is returned.
    """
    client = create_llm_client()
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=AGNES_MODEL, messages=messages, temperature=temperature
            )
            return response.choices[0].message.content or ""
        except openai.RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Agnes request did not return a response.")
