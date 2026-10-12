import copy

from wolf_api.agent.context import cache_breakpoint_count, system_message, with_cache_breakpoints


def transcript():
    return [
        system_message("rules"),
        {"role": "user", "content": "build an app"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "x", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "a", "content": '{"ok": true}'},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "b", "type": "function", "function": {"name": "y", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "b", "content": '{"ok": true}'},
    ]


def test_sliding_breakpoints_land_on_the_newest_messages_with_content():
    msgs = transcript()
    view = with_cache_breakpoints(msgs)
    # system + the two newest tool results; assistant tool-call-only messages are skipped
    assert cache_breakpoint_count(view) == 3 <= 4
    assert view[5]["content"][0]["cache_control"] and view[3]["content"][0]["cache_control"]
    assert view[1]["content"] == "build an app"


def test_the_stored_transcript_is_never_modified():
    msgs = transcript()
    before = copy.deepcopy(msgs)
    with_cache_breakpoints(msgs)
    assert msgs == before


def test_short_transcripts_and_list_content():
    view = with_cache_breakpoints([system_message("rules"), {"role": "user", "content": [{"type": "text", "text": "hi"}]}])
    assert cache_breakpoint_count(view) == 2
    assert view[1]["content"][0]["text"] == "hi"


# ─── Context offload: outline + get_screen ───────────────────────────────────

from wolf_api import config  # noqa: E402
from wolf_api.agent.prompts import snapshot_text  # noqa: E402
from wolf_api.agent.tools import execute  # noqa: E402
from wolf_api.schema import blank_schema  # noqa: E402


def big_schema(screens=12):
    schema = blank_schema("Big")
    for i in range(screens):
        execute(schema, "create_screen", {"name": f"Screen {i}"})
    for s in schema["screens"]:
        execute(schema, "add_components", {"screen_id": s["id"], "parent_id": s["root"]["id"], "components": [
            {"type": "Card", "style": {"padding": 16, "borderRadius": 16, "backgroundColor": "#FFFFFF"}, "children": [
                {"type": "Text", "props": {"text": f"A long realistic headline for {s['name']}", "variant": "title"}, "style": {"fontWeight": 700}},
                {"type": "Button", "props": {"label": "Continue", "variant": "filled", "icon": "arrow_forward"}},
            ]} for _ in range(3)
        ]})
    return schema


def test_small_projects_get_the_full_snapshot():
    text = snapshot_text(blank_schema("Small"))
    assert 'detail="outline"' not in text and '"padding":16' in text


def test_large_projects_get_an_outline_and_keep_the_selected_screen(monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_BUDGET_CHARS", 12000)
    schema = big_schema()
    selected = schema["screens"][3]["id"]
    full = snapshot_text(schema)
    outlined = snapshot_text(schema, {"screenId": selected})
    assert 'detail="outline"' in full and "get_screen" in full
    import json
    from wolf_api.agent.context import project_snapshot
    assert len(full) < len(json.dumps(project_snapshot(schema), separators=(",", ":"))) * 0.7
    # Outline nodes have labels but no styles; the selected screen stays in full.
    assert '"borderRadius"' not in full
    assert outlined.count('"borderRadius":16') == 3


def test_get_screen_returns_full_detail_and_changes_nothing():
    schema = big_schema(2)
    before = copy.deepcopy(schema)
    outcome = execute(schema, "get_screen", {"screen_id": schema["screens"][1]["id"]})
    assert outcome.change is None and schema == before
    card = outcome.result["root"]["children"][0]
    assert card["style"]["borderRadius"] == 16 and card["children"][1]["props"]["label"] == "Continue"


# ─── Structured compaction ───────────────────────────────────────────────────

from wolf_api.agent.context import checkpoint_message, tail_start, transcript_chars  # noqa: E402


def run_transcript(turns=6):
    msgs = [system_message("rules"), {"role": "user", "content": "request"}]
    for i in range(turns):
        msgs.append({"role": "assistant", "content": None, "tool_calls": [{"id": f"t{i}", "type": "function", "function": {"name": "add_components", "arguments": "x" * 1000}}]})
        msgs.append({"role": "tool", "tool_call_id": f"t{i}", "content": '{"ok":true}'})
    return msgs


def test_tail_starts_on_an_assistant_message():
    msgs = run_transcript()
    cut = tail_start(msgs, 2)
    assert msgs[cut]["role"] == "assistant" and len(msgs) - cut <= 6
    assert transcript_chars(msgs, 2) > 6000
    assert tail_start(run_transcript(1), 2) is None  # too short to fold anything


def test_checkpoint_keeps_the_request_and_progress():
    m = checkpoint_message("<request>\nbuild a plant app\n</request>", ["Created Home screen", "Updated the theme"])
    assert m["role"] == "user" and "build a plant app" in m["content"]
    assert "- Created Home screen" in m["content"] and "Don't redo" in m["content"]
