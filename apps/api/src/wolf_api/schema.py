"""Server-side helpers for the Wolf app schema (mirrors packages/schema/src/defaults.ts)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

DEFAULT_THEME = {
    "brightness": "light",
    "primary": "#6750A4",
    "secondary": "#625B71",
    "background": "#FFFBFE",
    "surface": "#FFFFFF",
    "text": "#1C1B1F",
    "mutedText": "#49454F",
    "radius": 12,
    "fontFamily": "Inter",
}


def blank_schema(name: str, description: str = "") -> dict[str, Any]:
    home_id = str(uuid.uuid4())
    slug = re.sub(r"[^a-z0-9]+", "", name.lower()) or "app"
    return {
        "version": 1,
        "name": name,
        "description": description,
        "theme": dict(DEFAULT_THEME),
        "screens": [{
            "id": home_id,
            "name": "Home",
            "root": {"id": str(uuid.uuid4()), "type": "Column", "name": "Screen", "props": {}, "style": {"padding": 16, "gap": 12}, "children": []},
            "frame": {"x": 0, "y": 0},
        }],
        "dataModels": [],
        "navigation": {"type": "stack", "initialScreenId": home_id, "tabs": []},
        "backend": {"provider": "none"},
        "build": {"appName": name, "bundleId": f"com.wolf.{slug}", "version": "1.0.0", "buildNumber": 1, "platforms": ["android", "ios"]},
    }


_STOP = re.compile(r"^(with|where|for|that|to|and|which|who|app|in|on|of|so|like)$", re.I)


def name_from_prompt(prompt: str) -> str:
    """'A habit tracker with streaks…' -> 'Habit Tracker'."""
    words = [re.sub(r"[^\w-]", "", w) for w in re.sub(r"^(an?|the|build|make|create)\s+", "", prompt.strip(), flags=re.I).split()]
    picked: list[str] = []
    for w in words:
        if not w or _STOP.match(w) or len(picked) == 3:
            break
        if w.lower() in ("a", "an", "the", "me", "my"):
            continue
        picked.append(w[:1].upper() + w[1:])
    return " ".join(picked) or "Untitled App"


class SchemaShape(BaseModel):
    """Minimal structural check for schemas saved from the editor."""

    model_config = ConfigDict(extra="allow")

    version: int
    name: str
    theme: dict[str, Any]
    screens: list[dict[str, Any]]
    dataModels: list[dict[str, Any]]
    navigation: dict[str, Any]
    backend: dict[str, Any]
    build: dict[str, Any]
