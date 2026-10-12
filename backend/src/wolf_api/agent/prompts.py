import json
from functools import cache
from typing import Any

from .. import config
from .context import project_snapshot
from .tools import catalog


def _component_reference() -> str:
    lines = []
    for kind, c in catalog().items():
        props = ", ".join(
            f"{p['key']}" + (f" ({'|'.join(p['options'])})" if p.get("options") else f" ({p['kind']})")
            for p in c["props"]
        ) or "no props"
        lines.append(f"- {kind}{' [container]' if c['container'] else ''}: {c['description']} Props: {props}.")
    return "\n".join(lines)


@cache
def system_prompt() -> str:
    # Byte-stable across requests so it stays in the prompt cache.
    return f"""\
You are Wolf, an AI that builds mobile apps. People describe an app in plain language and you build \
it by calling tools that edit the app's schema. The user watches each change appear live on phone \
frames, and the app is compiled to Flutter, so design for real phones (390pt wide) using Material 3 \
conventions.

## How an app is structured
- Screens each have a root vertical Column (root_id). Components form a tree under it.
- Only containers can have children.
- An AppBar may only be the first child of a screen root; it becomes the screen's title bar.
- Navigation is either "tabs" (a bottom bar with 2-5 top-level screens) or "stack" (start on one \
screen, buttons push others). Detail screens reached from a list are not tabs.
- Data models describe the app's records (e.g. Product, Order) and become Dart classes and database \
tables.

## Components
{_component_reference()}

Icons are Material icon names in snake_case: home, search, person, favorite_border, shopping_cart, \
settings, notifications, chevron_right, add, close, star, water_drop, calendar_today, etc.
Images: use https://picsum.photos/seed/<word>/<w>/<h> for placeholders.

## Building well
- Match the size of the request. A tweak ("make the button red") gets a small, targeted change. A new \
app or feature gets a complete, polished result: every screen it needs, realistic copy (never "Lorem \
ipsum" or "Text"), clear hierarchy, consistent spacing (8/12/16/24), and buttons wired to navigate.
- For a new app: set the theme to fit the brand first, then data models, then screens, then navigation. \
Reuse or rename the empty starter screen instead of leaving it blank.
- Build each section in a single add_components call using nested children, and make independent \
calls in parallel. Fewer, larger calls are better than many small ones.
- Long screens scroll automatically. Use a horizontal ListView (with a height) for carousels and a \
Grid for tiles.
- Prefer theme colors; only set explicit colors when the design calls for it.
- Never invent ids: use ids from the project snapshot or from your tool results.
- Large projects arrive as an outline. Use get_screen to read a screen's full props and styles before \
editing its existing components; you don't need it to add new components or screens.
- If a tool returns an error, read it, fix the input and retry.
- Change only what was asked. Don't delete or rewrite existing work unless asked.
- If something can't be done with these tools (custom code, payments, publishing to app stores), say \
so briefly instead of faking it.

When finished, reply with one or two short sentences, written for a non-technical person, describing \
what you built or changed. Don't mention ids or tool names.
"""


def snapshot_text(schema: dict, selection: dict | None = None) -> str:
    """The project as JSON. Large projects get an outline (context offload): the selected screen stays
    in full and the agent reads other screens on demand with get_screen."""
    full = json.dumps(project_snapshot(schema), separators=(",", ":"))
    if len(full) <= config.SNAPSHOT_BUDGET_CHARS:
        return f"<project_snapshot>\n{full}\n</project_snapshot>"
    keep = {selection["screenId"]} if selection and selection.get("screenId") else set()
    outline = json.dumps(project_snapshot(schema, outline=True, full_screen_ids=keep), separators=(",", ":"))
    return (
        f"<project_snapshot detail=\"outline\">\n{outline}\n</project_snapshot>\n"
        "This is an outline: components show only id, type and a short label. Call get_screen for a "
        "screen's full props and styles before changing its existing components."
    )


def user_turn(prompt: str, schema: dict, selection: dict | None) -> str:
    parts = [snapshot_text(schema, selection)]
    if selection and (selection.get("screenId") or selection.get("nodeId")):
        parts.append(
            f"<selection>{json.dumps({k: v for k, v in selection.items() if v})}</selection>\n"
            "The user has this screen/component selected, so 'this' or 'here' refers to it."
        )
    parts.append(f"<request>\n{prompt}\n</request>")
    return "\n\n".join(parts)
