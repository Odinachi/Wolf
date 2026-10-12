"""The tool-use loop: a prompt in, a stream of schema updates out."""

from __future__ import annotations

import copy
import json
import logging
from typing import Any, AsyncIterator

import anthropic

from .. import config
from .prompts import system_prompt, user_turn
from .tools import ToolError, execute, tool_definitions

log = logging.getLogger("wolf.agent")

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


def _event(name: str, **data: Any) -> dict[str, Any]:
    return {"event": name, "data": data}


async def run_agent(
    *,
    prompt: str,
    schema: dict,
    history: list[dict[str, str]],
    selection: dict | None = None,
    client: anthropic.AsyncAnthropic | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Edits a copy of `schema` and yields events:

    - change {text}: one human-readable change was made
    - schema {schema}: the schema after a batch of changes (persist and render this)
    - text {delta}: streamed reply text
    - error {message}: the run stopped early (changes so far are kept)
    - done {}
    """
    client = client or get_client()
    schema = copy.deepcopy(schema)
    tools = tool_definitions()

    # Earlier turns are replayed as plain text; only this turn carries the project snapshot.
    messages: list[Any] = [{"role": m["role"], "content": m["content"]} for m in history if m.get("content")]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": user_turn(prompt, schema, selection)})

    # Brand-new apps get more thinking than small edits.
    is_new_app = sum(len(s["root"]["children"]) for s in schema["screens"]) == 0
    effort = "high" if is_new_app else "medium"

    for _ in range(config.MAX_AGENT_TURNS):
        try:
            async with client.beta.messages.stream(
                model=config.MODEL,
                max_tokens=64000,
                system=system_prompt(),
                tools=tools,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": effort},
                cache_control={"type": "ephemeral"},
                # If a request is declined for safety reasons, the API retries it on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for text in stream.text_stream:
                    yield _event("text", delta=text)
                response = await stream.get_final_message()
        except anthropic.AuthenticationError:
            yield _event("error", message="The server's Anthropic API key is missing or invalid.")
            return
        except anthropic.RateLimitError:
            yield _event("error", message="The AI is busy right now. Try again in a moment.")
            return
        except anthropic.APIStatusError as e:
            log.exception("Anthropic API error")
            yield _event("error", message=f"The AI request failed ({e.status_code}).")
            return
        except anthropic.APIConnectionError:
            yield _event("error", message="Couldn't reach the AI service.")
            return

        # Appended unchanged (thinking and fallback blocks included).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            yield _event("error", message="The AI declined this request.")
            return
        if response.stop_reason == "max_tokens":
            yield _event("error", message="The AI ran out of room mid-change. Try a smaller request.")
            return

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break

        results = []
        changed = False
        for block in tool_uses:
            try:
                outcome = execute(schema, block.name, block.input)
            except ToolError as e:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True})
                continue
            changed = True
            yield _event("change", text=outcome.change)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(outcome.result)})
        if changed:
            yield _event("schema", schema=copy.deepcopy(schema))
        # All results for one assistant turn go back in a single user message.
        messages.append({"role": "user", "content": results})
    else:
        yield _event("error", message="The AI took too many steps and was stopped. Changes so far are kept.")
        return

    yield _event("done")
