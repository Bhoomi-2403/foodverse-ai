"""Shared Groq client + JSON helpers. The client is created lazily so the app starts without a key."""
import json
import logging
import re
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

import config

logger = logging.getLogger("foodverse.llm")
T = TypeVar("T", bound=BaseModel)

_client = None


class AIError(Exception):
    """Error that maps directly onto an HTTP response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def get_client():
    global _client
    key = config.groq_api_key()
    if not key:
        raise AIError(503, "GROQ_API_KEY is not configured on the server. Add it to backend/.env and restart.")
    if _client is None:
        from groq import Groq  # imported lazily

        _client = Groq(api_key=key, timeout=config.llm_timeout(), max_retries=1)
    return _client


def reset_client() -> None:
    global _client
    _client = None


def extract_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating code fences and surrounding prose."""
    if not text or not text.strip():
        raise AIError(502, "The AI model returned an empty response.")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIError(502, "The AI model returned a response that was not valid JSON.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            raise AIError(502, "The AI model returned malformed JSON.")
    if not isinstance(data, dict):
        raise AIError(502, "The AI model returned JSON in an unexpected shape.")
    return data


def image_part(b64: str, mime: str = "image/jpeg") -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def _map_exception(exc: Exception) -> AIError:
    import groq

    if isinstance(exc, groq.RateLimitError):
        return AIError(429, "The AI provider rate limit was reached. Please wait a moment and try again.")
    if isinstance(exc, groq.APITimeoutError):
        return AIError(504, "The AI provider timed out. Try again, or use a smaller image.")
    if isinstance(exc, groq.AuthenticationError):
        return AIError(503, "The AI provider rejected the API key. Check GROQ_API_KEY.")
    if isinstance(exc, groq.APIConnectionError):
        return AIError(503, "Could not reach the AI provider. Check the server's internet connection.")
    if isinstance(exc, groq.APIStatusError):
        return AIError(502, f"The AI provider returned an error (HTTP {exc.status_code}).")
    return AIError(502, "Unexpected error while calling the AI provider.")


def _is_model_missing(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    return status in (400, 404) and any(w in text for w in ("model", "decommission", "not found", "does not exist"))


def chat_json(messages: list[dict], *, vision: bool = False, temperature: float = 0.2, max_tokens: int = 2500) -> dict:
    """Call Groq and return a parsed JSON object. Tries fallback models if one is retired."""
    client = get_client()
    models = config.vision_models() if vision else config.text_models()
    last_error: Optional[AIError] = None

    for model in models:
        for use_json_mode in (True, False):
            kwargs: dict[str, Any] = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                completion = client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - mapped below
                if use_json_mode and getattr(exc, "status_code", None) == 400 and not _is_model_missing(exc):
                    logger.info("JSON mode rejected by %s; retrying without it", model)
                    continue
                if _is_model_missing(exc):
                    logger.warning("Model %s unavailable: %s", model, exc)
                    last_error = AIError(502, f"Model '{model}' is unavailable.")
                    break
                logger.error("Groq call failed (%s): %s", type(exc).__name__, exc)
                raise _map_exception(exc)
            content = completion.choices[0].message.content if completion.choices else ""
            return extract_json(content or "")
    raise last_error or AIError(502, "No configured AI model could handle the request.")


def run_validated(messages: list[dict], schema: Type[T], *, vision: bool = False, **kw) -> T:
    """Call the model, then validate against a Pydantic schema. Invalid output becomes a 502."""
    data = chat_json(messages, vision=vision, **kw)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        logger.error("Model output failed validation: %s", exc.errors()[:3])
        raise AIError(502, "The AI model's answer did not match the expected format. Please try again.")
