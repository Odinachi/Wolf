"""Small helpers for emitting Dart source safely."""

from __future__ import annotations

import keyword
import re
from typing import Any

_HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")

DART_RESERVED = {
    "abstract", "as", "assert", "async", "await", "break", "case", "catch", "class", "const",
    "continue", "default", "do", "else", "enum", "export", "extends", "false", "final", "finally",
    "for", "if", "import", "in", "is", "new", "null", "return", "super", "switch", "this",
    "throw", "true", "try", "var", "void", "while", "with",
}


def string(value: Any) -> str:
    """A single-quoted Dart string literal."""
    text = "" if value is None else str(value)
    text = (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("$", "\\$")
        .replace("\n", "\\n")
        .replace("\r", "")
    )
    return f"'{text}'"


def color(value: Any) -> str | None:
    """'#RRGGBB' or '#AARRGGBB' -> 'Color(0xAARRGGBB)'. None for anything else."""
    if not isinstance(value, str) or not _HEX.match(value):
        return None
    hexpart = value[1:].upper()
    if len(hexpart) == 6:
        hexpart = "FF" + hexpart
    return f"Color(0x{hexpart})"


def number(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if float(value).is_integer():
        return f"{int(value)}.0"
    return f"{float(value)}"


def edge_insets(value: Any) -> str | None:
    """A number (all sides) or [top, right, bottom, left]."""
    if isinstance(value, list) and len(value) == 4 and all(number(v) for v in value):
        top, right, bottom, left = (number(v) for v in value)
        return f"EdgeInsets.fromLTRB({left}, {top}, {right}, {bottom})"
    n = number(value)
    if n is None or n == "0.0":
        return None
    return f"EdgeInsets.all({n})"


def icon(name: Any) -> str:
    """A Material icon name like 'favorite_border' -> 'Icons.favorite_border'."""
    if isinstance(name, str):
        candidate = name.strip().lower().replace("-", "_").replace(" ", "_")
        if candidate in DART_RESERVED or keyword.iskeyword(candidate):
            candidate += "_"
        if _IDENT.match(candidate):
            return f"Icons.{candidate}"
    return "Icons.help_outline"


def pascal(name: str, fallback: str = "Item") -> str:
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    out = "".join(w[:1].upper() + w[1:] for w in words)
    if not out or not out[0].isalpha():
        out = fallback + out
    return out


def snake(name: str, fallback: str = "item") -> str:
    words = re.findall(r"[A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name or ""))
    out = "_".join(w.lower() for w in words)
    if not out or not out[0].isalpha():
        out = f"{fallback}_{out}".strip("_")
    if out in DART_RESERVED:
        out += "_"
    return out


def camel(name: str, fallback: str = "field") -> str:
    p = pascal(name, fallback.capitalize())
    out = p[:1].lower() + p[1:]
    if out in DART_RESERVED:
        out += "Value"
    return out


def indent(code: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in code.splitlines())
