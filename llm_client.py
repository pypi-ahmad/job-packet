"""LLM Client configuration for Job Packet supporting Agnes, OpenAI, and Google providers."""

import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
import openai
from openai import OpenAI

# Load .env if present without overriding existing process environment
load_dotenv()

# Constants
DEFAULT_AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_AGNES_MODEL = "agnes-3.0-flash"
GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_available_providers() -> Dict[str, Dict[str, object]]:
    """Detect available providers based on configured environment variables.
    
    Returns only providers that have their required API keys present.
    Never exposes or returns the actual keys.
    """
    providers: Dict[str, Dict[str, object]] = {}

    # Agnes AI (Primary default)
    agnes_key = os.getenv("AGNESAI_API_KEY")
    # Always include Agnes as default option; if key missing, UI can warn
    providers["Agnes AI"] = {
        "configured": bool(agnes_key and agnes_key.strip()),
        "base_url": os.getenv("AGNESAI_BASE_URL", DEFAULT_AGNES_BASE_URL),
        "models": [DEFAULT_AGNES_MODEL],
        "default_model": DEFAULT_AGNES_MODEL,
        "env_var": "AGNESAI_API_KEY",
    }

    # OpenAI (Optional extra provider)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.strip():
        providers["OpenAI"] = {
            "configured": True,
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "models": ["gpt-5.6-luna", "gpt-5.6-terra"],
            "default_model": "gpt-5.6-luna",
            "env_var": "OPENAI_API_KEY",
        }

    # Google Gemini (Optional extra provider via OpenAI-compatible endpoint)
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and google_key.strip():
        providers["Google Gemini"] = {
            "configured": True,
            "base_url": GOOGLE_OPENAI_BASE_URL,
            "models": ["gemini-3.5-flash-lite", "gemini-3.7-flash"],
            "default_model": "gemini-3.5-flash-lite",
            "env_var": "GOOGLE_API_KEY",
        }

    return providers


def create_llm_client(provider_name: str = "Agnes AI") -> OpenAI:
    """Instantiate official OpenAI SDK client for selected provider.
    
    Raises ValueError with missing variable name if required key is unset.
    Never prints or logs the key value.
    """
    providers = get_available_providers()
    if provider_name not in providers:
        raise ValueError(f"Provider '{provider_name}' is not recognized or available.")

    provider_info = providers[provider_name]
    env_var_name = str(provider_info["env_var"])
    api_key = os.getenv(env_var_name)

    if not api_key or not api_key.strip():
        raise ValueError(f"Required environment variable '{env_var_name}' is missing.")

    base_url = provider_info.get("base_url")

    if base_url:
        return OpenAI(api_key=api_key, base_url=str(base_url))
    return OpenAI(api_key=api_key)


def get_chat_completion(
    messages: List[Dict[str, str]],
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    max_retries: int = 5,
) -> str:
    """Generate chat completion via official OpenAI client with rate-limit retry."""
    providers = get_available_providers()
    provider_info = providers.get(provider_name)
    if not provider_info:
        raise ValueError(f"Provider '{provider_name}' not available.")

    selected_model = model or str(provider_info["default_model"])
    client = create_llm_client(provider_name)

    kwargs = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**kwargs)
            # Modest courtesy pause to avoid burst rate limits on free accounts
            time.sleep(1.0)
            return response.choices[0].message.content or ""
        except openai.RateLimitError as e:
            last_error = e
            wait_seconds = (attempt + 1) * 4
            time.sleep(wait_seconds)
        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                last_error = e
                wait_seconds = (attempt + 1) * 4
                time.sleep(wait_seconds)
            else:
                raise e

    if last_error:
        raise last_error
    return ""
