"""Application configuration sourced from the Windows process environment."""

import os

MODEL = "agnes-3.0-flash"
TEMPERATURE = 0
AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"


def agnes_key_is_set() -> bool:
    """Return whether the required Agnes credential is available.

    Returns:
        True when ``AGNESAI_API_KEY`` is present and non-blank in the current
        process environment. The key value is never returned or logged.
    """
    return bool(os.environ.get("AGNESAI_API_KEY", "").strip())
