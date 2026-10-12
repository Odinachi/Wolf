"""The agent harness: a prompt in, a stream of schema updates out. Runs on OpenRouter.

The orchestration follows "The Harness Effect" (arXiv 2607.06906): the loop, not the model, sets the
token bill, so it is built for it.
- Accounting: every turn's tokens, cache hits, cost and time are measured (accounting.py).
- Cache-shape discipline: an append-only transcript with sliding cache breakpoints (context.py).
- Context offload: outline snapshots, get_screen on demand, short per-run ids (context.py, aliases.py).
- Structured compaction: long runs fold into a checkpoint with a fresh snapshot (context.py).
- Failure-spend governance: typed failures, bounded retries, a fallback route plan, discarded
  attempts and a circuit breaker for repeated failing calls (failures.py).
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from .. import config
from .accounting import TurnUsage
from .aliases import IdAliases
from .context import checkpoint_message, system_message, tail_start, transcript_chars, with_cache_breakpoints
from .failures import Failure, backoff_seconds, call_signature, cap, classify, parse_arguments, route_plan
from .prompts import system_prompt, user_turn
from .tools import ToolError, execute, tool_definitions

log = logging.getLogger("wolf.agent")

RETRIES_PER_MODEL = 2  # attempts per model before falling through to the next one
MAX_TOOL_CALLS_PER_TURN = 12
REPEAT_FAILURE_LIMIT = 3  # identical failing calls before the circuit breaker stops the run

_client: AsyncOpenAI | None = None
_sleep = asyncio.sleep  # replaced in tests


class MissingApiKey(RuntimeError):
    pass


def get_client() -> AsyncOpenAI:
    global _client
    if not config.OPENROUTER_API_KEY:
        raise MissingApiKey("OPENROUTER_API_KEY is not set.")
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            # Optional attribution headers OpenRouter uses for its app rankings.
            default_headers={"HTTP-Referer": config.SITE_URL, "X-Title": "Wolf"},
        )
    return _client


def _event(name: str, **data: Any) -> dict[str, Any]:
    return {"event": name, "data": data}


@dataclass
class Attempt:
    """What one model call produced. Discarded entirely if the stream fails part-way."""

    text: str = ""
    calls: dict[int, dict[str, str]] = field(default_factory=dict)
    finish: str | None = None
    usage: Any = None


async def _stream(client: AsyncOpenAI, model: str, request: dict[str, Any], attempt: Attempt) -> AsyncIterator[str]:
    """One streamed model call. Yields text deltas and fills `attempt`; tools never run from here."""
    stream = await client.chat.completions.create(model=model, **request)
    async for chunk in stream:
        if getattr(chunk, "usage", None):
            attempt.usage = chunk.usage
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.delta
        if delta.content:
            attempt.text += delta.content
            yield delta.content
        for tc in delta.tool_calls or []:
            call = attempt.calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
            if tc.id:
                call["id"] = tc.id
            if tc.function and tc.function.name:
                call["name"] += tc.function.name
            if tc.function and tc.function.arguments:
                call["arguments"] += tc.function.arguments
        if choice.finish_reason:
            attempt.finish = choice.finish_reason


async def run_agent(
    *,
    prompt: str,
    schema: dict,
    history: list[dict[str, str]],
    selection: dict | None = None,
    client: AsyncOpenAI | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Edits a copy of `schema` and yields events:

    - change {text}: one human-readable change was made
    - schema {schema}: the schema after a batch of changes (persist and render this)
    - text {delta}: streamed reply text
    - discard {}: drop the streamed text so far (a failed attempt is being retried)
    - usage {...}: tokens, cache hits, cost and time for one model turn (internal)
    - compacted {folded}: older turns were folded into a checkpoint (internal)
    - error {message, kind}: the run stopped early (changes so far are kept); kind is a typed outcome
    - done {}
    """
    try:
        client = client or get_client()
    except MissingApiKey:
        yield _event("error", kind="missing_key", message="The server has no OpenRouter API key. Add OPENROUTER_API_KEY to backend/.env and restart the API.")
        return
    schema = copy.deepcopy(schema)
    tools = tool_definitions()
    ids = IdAliases()  # the model sees short ids (s1, c4, ...) instead of UUIDs

    # Earlier chat turns are replayed as plain text; only this request carries the project snapshot.
    history_msgs = [{"role": m["role"], "content": m["content"]} for m in history if m.get("content")]
    while history_msgs and history_msgs[0]["role"] != "user":
        history_msgs.pop(0)
    # The transcript is append-only for the whole run: the byte-stable prefix that prompt caching
    # prices at about a tenth of list (see context.py).
    messages: list[dict[str, Any]] = [
        system_message(system_prompt()),
        *history_msgs,
        {"role": "user", "content": ids.shorten(user_turn(prompt, schema, selection), schema)},
    ]
    opening = len(messages)  # system + earlier chat + this request; the run's own turns follow
    changes: list[str] = []
    failing_calls: dict[str, int] = {}

    # Brand-new apps get more reasoning than small edits.
    is_new_app = sum(len(s["root"]["children"]) for s in schema["screens"]) == 0
    extra_body: dict[str, Any] = {"usage": {"include": True}}  # OpenRouter reports cost per call
    if config.REASONING:
        extra_body["reasoning"] = {"effort": "high" if is_new_app else "medium"}

    for _ in range(config.MAX_AGENT_TURNS):
        # Structured compaction: fold older turns into a checkpoint once the transcript grows large.
        if transcript_chars(messages, opening) > config.COMPACT_AFTER_CHARS:
            cut = tail_start(messages, opening)
            if cut is not None:
                folded = cut - opening
                fresh = ids.shorten(user_turn(prompt, schema, selection), schema)
                messages = [*messages[: opening - 1], checkpoint_message(fresh, changes), *messages[cut:]]
                log.info("Compacted %d messages into a checkpoint (%d changes so far)", folded, len(changes))
                yield _event("compacted", folded=folded)

        request = {
            "messages": with_cache_breakpoints(messages),
            "tools": tools,
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": 32000,
            "extra_body": extra_body,
        }

        # One turn: try each model in the route plan, retrying transient failures with backoff.
        attempt: Attempt | None = None
        used_model = ""
        last_failure: Failure | None = None
        started = time.monotonic()
        for model in route_plan():
            for n in range(RETRIES_PER_MODEL):
                candidate = Attempt()
                streamed = False
                try:
                    async for delta in _stream(client, model, request, candidate):
                        streamed = True
                        yield _event("text", delta=delta)
                except Exception as e:  # classified below; nothing from this attempt is kept
                    last_failure = classify(e)
                    log.warning("Model call failed on %s (attempt %d): %s %s", model, n + 1, last_failure.kind, e)
                    if streamed:
                        yield _event("discard")
                    if last_failure.retryable and n + 1 < RETRIES_PER_MODEL:
                        await _sleep(backoff_seconds(n, last_failure))
                        continue
                    break
                attempt, used_model = candidate, model
                break
            if attempt is not None or (last_failure and not last_failure.fall_through):
                break
        if attempt is None:
            failure = last_failure or classify(RuntimeError("no model available"))
            yield _event("error", kind=failure.kind, message=failure.message)
            return

        yield _event("usage", **TurnUsage.from_usage(used_model, attempt.usage, int((time.monotonic() - started) * 1000), len(attempt.calls)).as_dict())

        if attempt.finish == "content_filter":
            yield _event("error", kind="declined", message="The AI declined this request.")
            return
        if attempt.finish == "length" and not attempt.calls:
            yield _event("error", kind="output_limit", message="The AI ran out of room mid-change. Try a smaller request.")
            return

        ordered = [attempt.calls[i] for i in sorted(attempt.calls)]
        assistant: dict[str, Any] = {"role": "assistant", "content": attempt.text or None}
        if ordered:
            assistant["tool_calls"] = [
                {"id": c["id"] or f"call_{i}", "type": "function", "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                for i, c in enumerate(ordered)
            ]
        messages.append(assistant)
        if not ordered:
            break

        changed = False
        stuck: str | None = None
        for i, tool_call in enumerate(assistant["tool_calls"]):
            fn = tool_call["function"]
            if i >= MAX_TOOL_CALLS_PER_TURN:
                content = f"Not run: at most {MAX_TOOL_CALLS_PER_TURN} calls per turn. Send this call again next turn."
            else:
                content, failed_signature = None, None
                try:
                    args = ids.expand(parse_arguments(fn["arguments"]))
                    outcome = execute(schema, fn["name"], args)
                except json.JSONDecodeError:
                    content = "Invalid JSON in tool arguments. Send the call again with valid JSON."
                    if attempt.finish == "length":
                        content += " Your output was cut off: send smaller batches (fewer components per call)."
                    failed_signature = f"{fn['name']}:invalid-json"
                except ToolError as e:
                    content = cap(ids.shorten(f"Error: {e}", schema))
                    failed_signature = call_signature(fn["name"], args)
                else:
                    if outcome.change:  # read-only tools (get_screen) change nothing
                        changed = True
                        changes.append(outcome.change)
                        yield _event("change", text=outcome.change)
                    content = ids.shorten(json.dumps(outcome.result, separators=(",", ":")), schema)

                # Circuit breaker: the same failing call again gets a nudge, then stops the run.
                if failed_signature:
                    failing_calls[failed_signature] = failing_calls.get(failed_signature, 0) + 1
                    count = failing_calls[failed_signature]
                    if count >= REPEAT_FAILURE_LIMIT:
                        stuck = fn["name"]
                    elif count == REPEAT_FAILURE_LIMIT - 1:
                        content += " This exact call has now failed twice: change the arguments or take a different approach."
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": content})

        if changed:
            yield _event("schema", schema=copy.deepcopy(schema))
        if stuck:
            log.warning("Circuit breaker: %s failed %d times with identical arguments", stuck, REPEAT_FAILURE_LIMIT)
            yield _event("error", kind="doom_loop", message="The AI got stuck repeating a step that kept failing, so it was stopped. Changes so far are kept.")
            return
    else:
        yield _event("error", kind="max_turns", message="The AI took too many steps and was stopped. Changes so far are kept.")
        return

    yield _event("done")
