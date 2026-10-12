"""The tool-use loop: a prompt in, a stream of schema updates out. Runs on OpenRouter."""

from __future__ import annotations

import copy
import json
import logging
import time
from typing import Any, AsyncIterator

import openai
from openai import AsyncOpenAI

from .. import config
from .accounting import TurnUsage
from .context import system_message, with_cache_breakpoints
from .prompts import system_prompt, user_turn
from .tools import ToolError, execute, tool_definitions

log = logging.getLogger("wolf.agent")

_client: AsyncOpenAI | None = None


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


def _error_message(e: openai.APIStatusError) -> str:
    if e.status_code == 401:
        return "The server's OpenRouter API key is invalid."
    if e.status_code == 402:
        return "The OpenRouter account is out of credits."
    if e.status_code == 429:
        return "The AI is busy right now. Try again in a moment."
    if e.status_code == 404:
        return f"The model '{config.MODEL}' isn't available on OpenRouter."
    return f"The AI request failed ({e.status_code})."


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
    - usage {...}: tokens, cache hits, cost and time for one model turn (see accounting.py)
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

    # Earlier turns are replayed as plain text; only this turn carries the project snapshot.
    history_msgs = [{"role": m["role"], "content": m["content"]} for m in history if m.get("content")]
    while history_msgs and history_msgs[0]["role"] != "user":
        history_msgs.pop(0)
    # The transcript is append-only for the whole run: the byte-stable prefix that prompt caching
    # prices at about a tenth of list (see context.py).
    messages: list[dict[str, Any]] = [
        system_message(system_prompt()),
        *history_msgs,
        {"role": "user", "content": user_turn(prompt, schema, selection)},
    ]

    # Brand-new apps get more reasoning than small edits.
    is_new_app = sum(len(s["root"]["children"]) for s in schema["screens"]) == 0
    extra_body: dict[str, Any] = {"usage": {"include": True}}  # OpenRouter reports cost per call
    if config.REASONING:
        extra_body["reasoning"] = {"effort": "high" if is_new_app else "medium"}

    for _ in range(config.MAX_AGENT_TURNS):
        text = ""
        calls: dict[int, dict[str, str]] = {}
        finish = None
        usage = None
        started = time.monotonic()
        try:
            stream = await client.chat.completions.create(
                model=config.MODEL,
                messages=with_cache_breakpoints(messages),
                tools=tools,
                stream=True,
                stream_options={"include_usage": True},
                max_tokens=32000,
                extra_body=extra_body,
            )
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta.content:
                    text += delta.content
                    yield _event("text", delta=delta.content)
                for tc in delta.tool_calls or []:
                    call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        call["id"] = tc.id
                    if tc.function and tc.function.name:
                        call["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        call["arguments"] += tc.function.arguments
                if choice.finish_reason:
                    finish = choice.finish_reason
        except openai.APIStatusError as e:
            log.warning("OpenRouter error %s: %s", e.status_code, e.message)
            yield _event("error", kind=f"http_{e.status_code}", message=_error_message(e))
            return
        except openai.APIConnectionError:
            yield _event("error", kind="connection", message="Couldn't reach OpenRouter.")
            return

        yield _event("usage", **TurnUsage.from_usage(config.MODEL, usage, int((time.monotonic() - started) * 1000), len(calls)).as_dict())

        if finish == "content_filter":
            yield _event("error", kind="declined", message="The AI declined this request.")
            return
        if finish == "length" and not calls:
            yield _event("error", kind="output_limit", message="The AI ran out of room mid-change. Try a smaller request.")
            return

        ordered = [calls[i] for i in sorted(calls)]
        assistant: dict[str, Any] = {"role": "assistant", "content": text or None}
        if ordered:
            assistant["tool_calls"] = [
                {"id": c["id"] or f"call_{i}", "type": "function", "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                for i, c in enumerate(ordered)
            ]
        messages.append(assistant)
        if not ordered:
            break

        changed = False
        for tool_call in assistant["tool_calls"]:
            fn = tool_call["function"]
            try:
                args = json.loads(fn["arguments"])
                outcome = execute(schema, fn["name"], args)
            except json.JSONDecodeError:
                content = "Invalid JSON in tool arguments. Send the call again with valid JSON."
            except ToolError as e:
                content = f"Error: {e}"
            else:
                changed = True
                yield _event("change", text=outcome.change)
                content = json.dumps(outcome.result)
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": content})
        if changed:
            yield _event("schema", schema=copy.deepcopy(schema))
    else:
        yield _event("error", kind="max_turns", message="The AI took too many steps and was stopped. Changes so far are kept.")
        return

    yield _event("done")
