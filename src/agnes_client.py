"""Agnes client with bounded 429 retries."""

import os
import time
from typing import Any

from openai import OpenAI, RateLimitError

from src.config import AGNES_BASE_URL, MODEL, TEMPERATURE


def chat_completion(
    messages: list[dict[str, str]],
    max_retries: int = 3,
    *,
    json_only: bool = False,
) -> Any:
    """Call Agnes with the fixed model and bounded HTTP 429 retries.

    Args:
        messages: OpenAI-compatible chat messages sent to Agnes.
        max_retries: Total attempts for a rate-limited request.
        json_only: When true, request a JSON object response format.

    Returns:
        The OpenAI SDK completion object.

    Raises:
        RuntimeError: If ``AGNESAI_API_KEY`` is absent or no request returns.
        RateLimitError: If every configured attempt receives HTTP 429.
    """
    api_key = os.environ.get("AGNESAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AGNESAI_API_KEY is not set")
    client = OpenAI(
        api_key=api_key,
        base_url=AGNES_BASE_URL,
        timeout=180.0,
        max_retries=0,
    )
    for attempt in range(max_retries):
        try:
            request: dict[str, Any] = {
                "model": MODEL,
                "temperature": TEMPERATURE,
                "messages": messages,
            }
            if json_only:
                request["response_format"] = {"type": "json_object"}
            return client.chat.completions.create(
                **request,
            )
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Agnes request failed")
