"""Per-turn token accounting (the harness's "trace shim").

Every model turn records prompt, completion and cached tokens, OpenRouter's reported cost and the
wall-clock time, so cost per task and cache hit rate are measurable per run and per release. What
isn't measured can't be managed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _get(obj: Any, name: str) -> Any:
    """Reads a field from an SDK object or dict, including provider extras (e.g. OpenRouter's cost)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    value = getattr(obj, name, None)
    if value is None:
        extra = getattr(obj, "model_extra", None) or {}
        value = extra.get(name)
    return value


@dataclass
class TurnUsage:
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost: float | None = None  # USD, as reported by OpenRouter
    duration_ms: int = 0
    tool_calls: int = 0

    @classmethod
    def from_usage(cls, model: str, usage: Any, duration_ms: int, tool_calls: int) -> "TurnUsage":
        details = _get(usage, "prompt_tokens_details")
        cost = _get(usage, "cost")
        return cls(
            model=model,
            prompt_tokens=int(_get(usage, "prompt_tokens") or 0),
            completion_tokens=int(_get(usage, "completion_tokens") or 0),
            cached_tokens=int(_get(details, "cached_tokens") or 0),
            cost=float(cost) if cost is not None else None,
            duration_ms=duration_ms,
            tool_calls=tool_calls,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunUsage:
    """Totals for one AI run (one user request)."""

    turns: list[dict[str, Any]] = field(default_factory=list)

    def add(self, turn: dict[str, Any]) -> None:
        self.turns.append(turn)

    def _sum(self, key: str) -> int:
        return sum(int(t.get(key) or 0) for t in self.turns)

    @property
    def prompt_tokens(self) -> int:
        return self._sum("prompt_tokens")

    @property
    def completion_tokens(self) -> int:
        return self._sum("completion_tokens")

    @property
    def cached_tokens(self) -> int:
        return self._sum("cached_tokens")

    @property
    def cost(self) -> float | None:
        costs = [t.get("cost") for t in self.turns]
        return round(sum(c for c in costs if c is not None), 6) if any(c is not None for c in costs) else None

    @property
    def cache_hit_rate(self) -> float:
        return round(self.cached_tokens / self.prompt_tokens, 3) if self.prompt_tokens else 0.0
