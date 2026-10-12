"""Context assembly for the agent loop.

Implements the harness paper's cache-shape discipline: every request is a byte-stable prefix
(tool schemas, system prompt, the append-only transcript) and nothing that changes per turn is
allowed into it. Provider cache breakpoints are placed on a copy of the transcript sent to the API,
never stored, so the transcript itself stays byte-identical from turn to turn.
"""

from __future__ import annotations

import copy
from typing import Any

EPHEMERAL = {"type": "ephemeral"}
# Anthropic allows four breakpoints per request: one after the tools + system prompt, and these
# sliding ones on the newest turns, so each turn reuses everything the previous turn already paid for.
SLIDING_BREAKPOINTS = 2


def system_message(text: str) -> dict[str, Any]:
    """The stable system prompt, with the first cache breakpoint (it also covers the tool schemas,
    which providers place before the system prompt)."""
    return {"role": "system", "content": [{"type": "text", "text": text, "cache_control": EPHEMERAL}]}


def _mark(message: dict[str, Any]) -> dict[str, Any] | None:
    """A copy of the message with a cache breakpoint on its last content part, or None if it has no
    content to mark (e.g. an assistant message that only carries tool calls)."""
    content = message.get("content")
    if not content:
        return None
    marked = dict(message)
    if isinstance(content, str):
        marked["content"] = [{"type": "text", "text": content, "cache_control": EPHEMERAL}]
    else:
        parts = copy.deepcopy(content)
        parts[-1] = {**parts[-1], "cache_control": EPHEMERAL}
        marked["content"] = parts
    return marked


def with_cache_breakpoints(messages: list[dict[str, Any]], sliding: int = SLIDING_BREAKPOINTS) -> list[dict[str, Any]]:
    """Returns the request view of the transcript: the newest `sliding` messages that have content
    get a cache breakpoint. The input list is not modified."""
    view = list(messages)
    remaining = sliding
    for i in range(len(view) - 1, 0, -1):  # never index 0: the system message has its own breakpoint
        if remaining == 0:
            break
        if view[i].get("role") == "system":
            continue
        marked = _mark(view[i])
        if marked is not None:
            view[i] = marked
            remaining -= 1
    return view


def cache_breakpoint_count(messages: list[dict[str, Any]]) -> int:
    count = 0
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            count += sum(1 for part in content if isinstance(part, dict) and part.get("cache_control"))
    return count


# ─── Project snapshot: full detail, or an outline with on-demand detail ─────


def compact_node(node: dict) -> dict:
    """A component tree with everything the model needs to edit it."""
    out: dict[str, Any] = {"id": node["id"], "type": node["type"]}
    for key in ("name", "props", "style", "onTap"):
        if node.get(key):
            out[key] = node[key]
    if node.get("children"):
        out["children"] = [compact_node(c) for c in node["children"]]
    return out


def outline_node(node: dict) -> dict:
    """Just the shape of a tree: ids, types and a short label. Props and styles come from get_screen."""
    out: dict[str, Any] = {"id": node["id"], "type": node["type"]}
    props = node.get("props") or {}
    label = node.get("name") or props.get("title") or props.get("text") or props.get("label")
    if label:
        out["label"] = str(label)[:40]
    if node.get("children"):
        out["children"] = [outline_node(c) for c in node["children"]]
    return out


def project_snapshot(schema: dict, *, outline: bool = False, full_screen_ids: set[str] = frozenset()) -> dict[str, Any]:
    def screen(s: dict) -> dict:
        detailed = not outline or s["id"] in full_screen_ids
        return {
            "id": s["id"], "name": s["name"], "root_id": s["root"]["id"], "backgroundColor": s.get("backgroundColor"),
            "root": compact_node(s["root"]) if detailed else outline_node(s["root"]),
        }

    return {
        "app": {"name": schema["name"], "description": schema.get("description", "")},
        "theme": schema["theme"],
        "navigation": schema["navigation"],
        "dataModels": schema["dataModels"],
        "screens": [screen(s) for s in schema["screens"]],
    }
