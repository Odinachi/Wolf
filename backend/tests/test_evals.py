import asyncio
import copy

from test_agent import FakeClient, turn

from evals.run import Report, TaskResult, check, gate, load_tasks, run_eval, seed_schema


def test_tasks_are_locked_and_seeds_load():
    tasks = load_tasks()
    assert {t["id"] for t in tasks} >= {"new-small", "new-10-screens", "edit-theme", "edit-add-screen", "edit-copy", "edit-navigation"}
    for t in tasks:
        schema = seed_schema(t)
        assert schema["screens"] and "checks" in t


def test_checks_score_structure():
    task = next(t for t in load_tasks() if t["id"] == "edit-theme")
    before = seed_schema(task)
    after = copy.deepcopy(before)
    assert check(task, before, after) == {"theme_brightness": False, "compiles": True}
    after["theme"]["brightness"] = "dark"
    assert all(check(task, before, after).values())


def test_run_eval_with_a_fake_model_reports_cost_and_quality():
    task = next(t for t in load_tasks() if t["id"] == "edit-theme")
    fake = FakeClient([
        turn(calls=[("t1", "set_theme", {"brightness": "dark", "primary": "#F97316"})], usage=(9000, 200, 7000, 0.0011)),
        turn(texts=["Dark with orange."], usage=(9400, 20, 9000, 0.0002)),
    ])
    report = asyncio.run(run_eval([task], client=fake))
    r = report.results[0]
    assert r.outcome == "completed" and r.quality == 1.0 and r.turns == 2 and r.changes == 1
    s = report.summary()
    assert abs(s["cost_per_task"] - 0.0013) < 1e-9 and s["cache_hit_rate"] > 0.8 and s["cpm"] > 0


def _report(cost, quality):
    r = TaskResult("t", "completed", quality, {}, 1, 1000, 0, 100, cost, 1.0, 1)
    return Report("m", "now", [r]).summary()


def test_release_gate():
    base = _report(0.010, 0.9)
    assert gate(_report(0.0105, 0.9), base) == []  # within 10%
    assert "cost per task" in gate(_report(0.012, 0.9), base)[0]
    assert "quality fell" in gate(_report(0.010, 0.8), base)[0]
