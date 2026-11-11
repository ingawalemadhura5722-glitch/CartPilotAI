"""
The ONLY place that talks to Google Gemini (official google-genai SDK).

- Reads GEMINI_API_KEY / GEMINI_MODEL from backend/.env (never from the frontend).
- generate_json() asks Gemini for JSON and validates it with a Pydantic model.
- Every failure becomes a GeminiServiceError with a friendly message and
  an HTTP status, so the API can answer clearly instead of crashing.
"""

import json
import logging
import os
import re
from functools import lru_cache
from typing import List, Optional, Type, TypeVar
import time
import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("cartpilot.gemini")

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "gemini-3.8-flash"
PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here", "your_api_key_here", "changeme"}


class GeminiServiceError(Exception):
    """A problem talking to Gemini, with a user-friendly message."""

    def __init__(self, code: str, message: str, http_status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def get_model_name() -> str:
    return (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
def get_model_candidates() -> List[str]:
    """Main model first, then any backups from GEMINI_FALLBACK_MODELS."""
    primary = get_model_name()
    extras = [m.strip() for m in (os.getenv("GEMINI_FALLBACK_MODELS") or "").split(",") if m.strip()]
    return [primary] + [m for m in extras if m != primary]

def _timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("GEMINI_TIMEOUT_SECONDS", "40")))
    except ValueError:
        return 40.0


def _get_api_key() -> str:
    key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if key.lower() in PLACEHOLDER_KEYS:
        raise GeminiServiceError(
            "missing_api_key",
            "The Gemini API key is not configured. Add GEMINI_API_KEY to backend/.env and restart the backend.",
            503,
        )
    return key


def is_configured() -> bool:
    try:
        _get_api_key()
        return True
    except GeminiServiceError:
        return False


@lru_cache(maxsize=2)
def _client_for(api_key: str, timeout_ms: int) -> genai.Client:
    """Create (and reuse) one Gemini client. timeout is in milliseconds."""
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))


def _translate_exception(exc: Exception) -> GeminiServiceError:
    """Convert any SDK / network error into a GeminiServiceError."""
    if isinstance(exc, GeminiServiceError):
        return exc

    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return GeminiServiceError(
            "timeout", "Gemini took too long to respond. Please try again in a moment.", 504
        )

    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        text = str(getattr(exc, "message", None) or exc)
        lowered = text.lower()

        if code == 429 or "resource_exhausted" in lowered or "quota" in lowered:
            return GeminiServiceError(
                "quota_exceeded",
                "The Gemini quota or rate limit has been reached. Wait a minute and try again, "
                "or check your usage limits in Google AI Studio.",
                429,
            )
        if code in (401, 403) or "api key not valid" in lowered or "api_key_invalid" in lowered:
            return GeminiServiceError(
                "invalid_api_key",
                "Gemini rejected the API key. Check GEMINI_API_KEY in backend/.env and restart the backend.",
                503,
            )
        if code == 404:
            return GeminiServiceError(
                "model_not_found",
                f"The Gemini model '{get_model_name()}' was not found. "
                "Set GEMINI_MODEL in backend/.env to a model that is available to your key.",
                503,
            )
        if code == 400:
            return GeminiServiceError(
                "bad_request", "Gemini could not process this request. Try rephrasing your message.", 502
            )
        if code is not None and code >= 500:
            return GeminiServiceError(
                "gemini_unavailable", "Gemini is temporarily unavailable. Please try again shortly.", 503
            )
        return GeminiServiceError("gemini_error", "Gemini returned an unexpected error.", 502)

    if isinstance(exc, httpx.HTTPError):
        return GeminiServiceError(
            "network_error", "Could not reach Gemini. Check the backend's internet connection.", 502
        )

    logger.exception("Unexpected error while calling Gemini")
    return GeminiServiceError("unexpected_error", "Something went wrong while contacting the AI.", 502)


def _extract_json(text: str) -> dict:
    """Parse JSON, tolerating accidental ```json fences or extra text around it."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise

# Temporary Google-side problems: worth trying another model (or waiting briefly).
TRANSIENT_CODES = {"gemini_unavailable"}


def _generate_with_fallback(client, models: List[str], prompt: str, system_instruction: str):
    """
    Try each model in order. If Gemini is overloaded (503), move on to the next
    model; after one full pass, wait briefly and make a second pass.
    """
    last_error: Optional[GeminiServiceError] = None

    for pass_number in range(2):
        for model in models:
            try:
                return client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                    ),
                )
            except Exception as exc:  # noqa: BLE001  (we translate every failure)
                error = _translate_exception(exc)
                logger.warning("Gemini call failed on '%s' (%s): %s", model, error.code, exc)

                is_backup = model != models[0]
                if error.code in TRANSIENT_CODES or (error.code == "model_not_found" and is_backup):
                    last_error = error
                    continue  # try the next model
                raise error from exc

        if pass_number == 0:
            time.sleep(2)

    raise last_error or GeminiServiceError(
        "gemini_unavailable", "Gemini is temporarily unavailable. Please try again shortly.", 503
    )


def generate_json(system_instruction: str, prompt: str, schema: Type[T], attempts: int = 2) -> T:
    """
    Ask Gemini for a JSON object and validate it with the given Pydantic model.
    Falls back to backup models when the main one is overloaded, and retries
    once if the JSON is malformed or fails validation.
    """
    client = _client_for(_get_api_key(), int(_timeout_seconds() * 1000))
    models = get_model_candidates()

    for attempt in range(1, attempts + 1):
        response = _generate_with_fallback(client, models, prompt, system_instruction)

        text: Optional[str] = response.text
        try:
            if not text:
                raise ValueError("Gemini returned an empty response")
            return schema.model_validate(_extract_json(text))
        except (ValueError, ValidationError) as exc:
            logger.warning("Gemini JSON problem on attempt %d/%d: %s", attempt, attempts, exc)

    raise GeminiServiceError(
        "bad_ai_response", "The AI returned an unexpected response. Please try again.", 502
    )