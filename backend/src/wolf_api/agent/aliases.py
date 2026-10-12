"""Short per-run ids for the model.

The schema uses UUIDs, which are long and split into many tokens; in a 10-screen app they make up
around 40% of the project snapshot and appear again in every tool call and result. The model instead
sees short aliases that are stable for the run (s1, s2 for screens, c1 for components, m1 for data
models, f1 for fields), and the harness translates them back before tools run. Shorter ids are also
easier for small models to copy correctly.
"""

from __future__ import annotations

import re
from typing import Any

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _kinds(schema: dict) -> dict[str, str]:
    """uuid -> alias prefix for every id in the schema."""
    kinds: dict[str, str] = {}

    def walk(node: dict) -> None:
        kinds[node["id"]] = "c"
        for child in node.get("children") or []:
            walk(child)

    for screen in schema.get("screens") or []:
        kinds[screen["id"]] = "s"
        walk(screen["root"])
    for model in schema.get("dataModels") or []:
        kinds[model["id"]] = "m"
        for f in model.get("fields") or []:
            kinds[f["id"]] = "f"
    return kinds


def _is_id_key(key: str) -> bool:
    return key.endswith(("_id", "Id", "_ids", "Ids"))


class IdAliases:
    def __init__(self) -> None:
        self.to_alias: dict[str, str] = {}
        self.to_id: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def _alias(self, uuid: str, prefix: str) -> str:
        alias = self.to_alias.get(uuid)
        if alias is None:
            self._counts[prefix] = self._counts.get(prefix, 0) + 1
            alias = f"{prefix}{self._counts[prefix]}"
            self.to_alias[uuid] = alias
            self.to_id[alias] = uuid
        return alias

    def shorten(self, text: str, schema: dict) -> str:
        """Replaces every UUID in text the model will read with its alias (assigned in order of
        appearance, so the same text always shortens to the same bytes)."""
        kinds = _kinds(schema)
        return UUID.sub(lambda m: self._alias(m.group(0), kinds.get(m.group(0), "x")), text)

    def expand(self, value: Any, key: str = "") -> Any:
        """Translates aliases back to UUIDs in id-like fields of tool arguments. Unknown values (including
        real UUIDs) pass through untouched."""
        if isinstance(value, dict):
            return {k: self.expand(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.expand(v, key) for v in value]
        if isinstance(value, str) and _is_id_key(key):
            return self.to_id.get(value, value)
        return value
