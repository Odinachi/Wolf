"""Failure-spend governance for the agent loop.

Every failure is classified into a typed class before anything is decided. Only transient classes are
retried (with backoff), and only whitelisted classes fall through to the next model in the route
plan; everything else stops the run with a clear message. Retries, dead ends and doom loops multiply
the token bill, so the harness bounds them explicitly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx2
import openai

from .. import config


@dataclass(frozen=True)
class Failure:
    kind: str  # typed outcome, saved on the run
    retryable: bool  # worth trying the same model again
    fall_through: bool  # worth trying the next model in the route plan
    message: str  # shown to the user if the run stops
    retry_after: float | None = None


def classify(error: BaseException) -> Failure:
    if isinstance(error, openai.APIStatusError):
        status = error.status_code
        retry_after = _retry_after(error.response)
        if status == 429:
            return Failure("rate_limit", True, True, "The AI is busy right now. Try again in a moment.", retry_after)
        if status in (500, 502, 503, 504, 529):
            return Failure("provider_outage", True, True, "The AI provider is having trouble. Try again in a moment.", retry_after)
        if status == 401 or status == 403:
            return Failure("auth", False, False, "The server's OpenRouter API key is invalid.")
        if status == 402:
            return Failure("credits", False, False, "The OpenRouter account is out of credits.")
        if status == 404:
            return Failure("model_unavailable", False, True, f"The model '{config.MODEL}' isn't available on OpenRouter.")
        if status in (400, 413, 422):
            return Failure("bad_request", False, False, f"The AI rejected the request ({status}).")
        return Failure(f"http_{status}", False, False, f"The AI request failed ({status}).")
    if isinstance(error, openai.APITimeoutError):
        return Failure("timeout", True, True, "The AI took too long to respond.")
    if isinstance(error, openai.APIConnectionError):
        return Failure("connection", True, True, "Couldn't reach OpenRouter.")
    # Anything else while streaming: a truncated or malformed stream.
    return Failure("malformed_stream", True, True, "The AI's response was cut off.")


def _retry_after(response: httpx2.Response | None) -> float | None:
    try:
        value = response.headers.get("retry-after") if response is not None else None
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def backoff_seconds(attempt: int, failure: Failure) -> float:
    """Exponential backoff (0.5s, 1s, 2s...), honoring Retry-After up to a cap."""
    base = 0.5 * (2 ** attempt)
    return min(max(base, failure.retry_after or 0), 10.0)


def route_plan() -> list[str]:
    """Which models to use, in fallback order. Configuration, never code that branches on a model."""
    plan = [config.MODEL, *config.FALLBACK_MODELS]
    return list(dict.fromkeys(m for m in plan if m))


# ─── Tool-call hygiene (a floor that holds for weaker models) ─────────────────

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def parse_arguments(raw: str) -> object:
    """Parses tool arguments, recovering common slips: empty strings, ```json fences, and JSON that was
    encoded twice (a string containing JSON). Raises json.JSONDecodeError if it can't be recovered."""
    text = (raw or "").strip() or "{}"
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    value = json.loads(text)
    if isinstance(value, str):
        value = json.loads(value)
    return value


def call_signature(name: str, args: object) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True, separators=(',', ':'))}"


def cap(message: str, limit: int = 1500) -> str:
    return message if len(message) <= limit else message[: limit - 1] + "…"
