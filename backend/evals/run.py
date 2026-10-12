"""Locked evaluation tasks for the agent harness, with a release gate.

Following the harness paper's method: a fixed task set and a frozen baseline, so a change to prompts,
tools or orchestration can be judged on cost, tokens, latency and quality before it ships.

    cd backend
    uv run python -m evals.run                      # run all tasks with WOLF_MODEL
    uv run python -m evals.run --model anthropic/claude-sonnet-5.5 --tasks new-small,edit-theme
    uv run python -m evals.run --save-baseline      # freeze this run as evals/baseline.json
    uv run python -m evals.run --baseline evals/baseline.json   # exit 1 if the gate fails

Needs OPENROUTER_API_KEY. Every run spends real tokens.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wolf_flutter import generate_project

from wolf_api import config
from wolf_api.agent.accounting import RunUsage
from wolf_api.agent.runner import run_agent
from wolf_api.schema import blank_schema, name_from_prompt

HERE = Path(__file__).resolve().parent
COST_REGRESSION = 0.10  # gate: cost per task may not rise more than 10%
QUALITY_REGRESSION = 0.05  # gate: mean quality may not drop more than 0.05


def load_tasks(only: set[str] | None = None) -> list[dict[str, Any]]:
    tasks = json.loads((HERE / "tasks.json").read_text())
    return [t for t in tasks if not only or t["id"] in only]


def seed_schema(task: dict[str, Any]) -> dict[str, Any]:
    if task.get("seed"):
        return json.loads((HERE / "seeds" / f"{task['seed']}.json").read_text())
    return blank_schema(name_from_prompt(task["prompt"]), task["prompt"])


def _walk(node: dict):
    yield node
    for child in node.get("children") or []:
        yield from _walk(child)


def check(task: dict[str, Any], before: dict, after: dict) -> dict[str, bool]:
    """Structural quality checks; each is pass/fail."""
    c = task["checks"]
    nodes = [n for s in after["screens"] for n in _walk(s["root"])]
    results: dict[str, bool] = {}
    if "min_screens" in c:
        results["min_screens"] = len(after["screens"]) >= c["min_screens"]
    if c.get("no_empty_screens"):
        results["no_empty_screens"] = all(s["root"]["children"] for s in after["screens"])
    if "navigation" in c:
        nav = after["navigation"]
        results["navigation"] = nav["type"] == c["navigation"] and (c["navigation"] != "tabs" or len(nav["tabs"]) >= 2)
    if "theme_brightness" in c:
        results["theme_brightness"] = after["theme"].get("brightness") == c["theme_brightness"]
    if c.get("screen_added"):
        results["screen_added"] = len(after["screens"]) > len(before["screens"])
    if "has_component" in c:
        results["has_component"] = any(n["type"] == c["has_component"] for n in nodes)
    if "text_contains" in c:
        needle = c["text_contains"].lower()
        results["text_contains"] = any(needle in str((n.get("props") or {}).get("text", "")).lower() for n in nodes)
    if c.get("compiles"):
        results["compiles"] = not generate_project(after).warnings
    return results


@dataclass
class TaskResult:
    id: str
    outcome: str
    quality: float
    checks: dict[str, bool]
    turns: int
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    cost: float | None
    seconds: float
    changes: int

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


async def run_task(task: dict[str, Any], client=None) -> TaskResult:
    before = seed_schema(task)
    after = copy.deepcopy(before)
    usage, outcome, changes = RunUsage(), "stopped", 0
    selection = None
    if task.get("selection"):
        screen = next(s for s in before["screens"] if s["name"].lower() == task["selection"])
        selection = {"screenId": screen["id"], "nodeId": screen["root"]["id"]}
    started = time.monotonic()
    async for e in run_agent(prompt=task["prompt"], schema=before, history=[], selection=selection, client=client):
        kind, data = e["event"], e["data"]
        if kind == "usage":
            usage.add(data)
        elif kind == "schema":
            after = data["schema"]
        elif kind == "change":
            changes += 1
        elif kind == "done":
            outcome = "completed"
        elif kind == "error":
            outcome = data.get("kind", "error")
    checks = check(task, before, after)
    quality = round(sum(checks.values()) / len(checks), 3) if checks else 0.0
    return TaskResult(
        id=task["id"], outcome=outcome, quality=quality if outcome == "completed" else round(quality * 0.5, 3),
        checks=checks, turns=len(usage.turns), prompt_tokens=usage.prompt_tokens, cached_tokens=usage.cached_tokens,
        completion_tokens=usage.completion_tokens, cost=usage.cost, seconds=round(time.monotonic() - started, 1), changes=changes,
    )


@dataclass
class Report:
    model: str
    created_at: str
    results: list[TaskResult] = field(default_factory=list)

    def summary(self) -> dict[str, float]:
        n = len(self.results) or 1
        tokens = sum(r.tokens for r in self.results)
        prompt = sum(r.prompt_tokens for r in self.results)
        costs = [r.cost for r in self.results if r.cost is not None]
        cost_per_task = round(sum(costs) / len(costs), 6) if costs else 0.0
        quality = round(sum(r.quality for r in self.results) / n, 3)
        return {
            "tasks": len(self.results),
            "quality": quality,
            "cost_per_task": cost_per_task,
            "tokens_per_task": round(tokens / n),
            "cache_hit_rate": round(sum(r.cached_tokens for r in self.results) / prompt, 3) if prompt else 0.0,
            "median_seconds": sorted(r.seconds for r in self.results)[len(self.results) // 2] if self.results else 0.0,
            # The paper's efficiency metrics: quality per dollar and task-completions per million tokens.
            "quality_per_dollar": round(quality / cost_per_task, 2) if cost_per_task else 0.0,
            "cpm": round(sum(r.quality for r in self.results) * 1e6 / tokens, 1) if tokens else 0.0,
        }

    def to_json(self) -> dict[str, Any]:
        return {"model": self.model, "created_at": self.created_at, "summary": self.summary(), "results": [asdict(r) for r in self.results]}


def gate(current: dict[str, float], baseline: dict[str, float]) -> list[str]:
    """Release gate: returns the reasons this run fails against the baseline (empty = pass)."""
    problems = []
    if baseline.get("cost_per_task") and current["cost_per_task"] > baseline["cost_per_task"] * (1 + COST_REGRESSION):
        problems.append(f"cost per task rose from ${baseline['cost_per_task']:.4f} to ${current['cost_per_task']:.4f}")
    if current["quality"] < baseline.get("quality", 0) - QUALITY_REGRESSION:
        problems.append(f"quality fell from {baseline['quality']:.2f} to {current['quality']:.2f}")
    return problems


def print_report(report: Report) -> None:
    print(f"\nModel: {report.model}\n")
    print(f"{'task':18} {'outcome':16} {'quality':>7} {'turns':>5} {'in':>8} {'cached':>8} {'out':>7} {'cost':>9} {'secs':>6}")
    for r in report.results:
        cost = f"${r.cost:.4f}" if r.cost is not None else "n/a"
        print(f"{r.id:18} {r.outcome:16} {r.quality:7.2f} {r.turns:5} {r.prompt_tokens:8} {r.cached_tokens:8} {r.completion_tokens:7} {cost:>9} {r.seconds:6.1f}")
        failed = [k for k, ok in r.checks.items() if not ok]
        if failed:
            print(f"{'':18} failed checks: {', '.join(failed)}")
    s = report.summary()
    print(
        f"\nquality {s['quality']:.2f} · cost/task ${s['cost_per_task']:.4f} · tokens/task {s['tokens_per_task']} · "
        f"cache hit {s['cache_hit_rate']:.0%} · median {s['median_seconds']}s · quality/$ {s['quality_per_dollar']} · CPM {s['cpm']}"
    )


async def run_eval(tasks: list[dict[str, Any]], client=None) -> Report:
    report = Report(model=config.MODEL, created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for task in tasks:
        print(f"Running {task['id']}…", file=sys.stderr)
        report.results.append(await run_task(task, client))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", help="override WOLF_MODEL for this run")
    parser.add_argument("--tasks", help="comma-separated task ids")
    parser.add_argument("--baseline", type=Path, help="compare with a saved report and fail on regressions")
    parser.add_argument("--save-baseline", action="store_true", help="save this run as evals/baseline.json")
    args = parser.parse_args()
    if args.model:
        config.MODEL = args.model
    if not config.OPENROUTER_API_KEY:
        print("Set OPENROUTER_API_KEY (backend/.env) to run evals.", file=sys.stderr)
        return 2

    tasks = load_tasks(set(args.tasks.split(",")) if args.tasks else None)
    report = asyncio.run(run_eval(tasks))
    print_report(report)

    out = HERE / "reports" / f"{report.created_at.replace(':', '')}-{config.MODEL.replace('/', '_')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report.to_json(), indent=1))
    print(f"\nReport: {out}")
    if args.save_baseline:
        (HERE / "baseline.json").write_text(json.dumps(report.to_json(), indent=1))
        print("Saved as evals/baseline.json")
    if args.baseline:
        problems = gate(report.summary(), json.loads(args.baseline.read_text())["summary"])
        if problems:
            print("\nRelease gate FAILED: " + "; ".join(problems))
            return 1
        print("\nRelease gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
