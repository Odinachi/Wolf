import json
from types import SimpleNamespace

import pytest

from wolf_api.agent import runner
from wolf_api.agent.tools import ToolError, execute, tool_definitions
from wolf_api.schema import blank_schema


def run(schema, name, args):
    return execute(schema, name, args)


# ─── Tools ───────────────────────────────────────────────────────────────────


def test_tool_definitions_are_well_formed():
    defs = [d["function"] for d in tool_definitions()]
    assert len({d["name"] for d in defs}) == len(defs)
    assert all(d["description"] and d["parameters"]["type"] == "object" for d in defs)


def test_build_a_screen():
    schema = blank_schema("Test")
    home = schema["screens"][0]
    detail = run(schema, "create_screen", {"name": "Detail"}).result
    assert schema["screens"][1]["frame"]["x"] == 510

    out = run(schema, "add_components", {"screen_id": home["id"], "parent_id": home["root"]["id"], "components": [
        {"type": "AppBar", "props": {"title": "Home"}},
        {"type": "Card", "style": {"padding": 16}, "children": [
            {"type": "Text", "props": {"text": "Hello", "variant": "title"}},
            {"type": "Button", "props": {"label": "Open"}, "on_tap": {"type": "navigate", "screenId": detail["screen_id"]}},
        ]},
    ]})
    card = home["root"]["children"][1]
    assert card["type"] == "Card" and card["style"]["borderRadius"] == 16  # catalog default kept
    assert card["children"][1]["onTap"] == {"type": "navigate", "screenId": detail["screen_id"]}
    assert card["children"][1]["props"]["variant"] == "filled"  # default prop filled in
    text_id = out.result["created"][1]["children"][0]["id"]

    run(schema, "update_component", {"screen_id": home["id"], "component_id": text_id, "props": {"text": "Hi"}, "style": {"color": "#FF0000"}})
    assert card["children"][0]["props"]["text"] == "Hi" and card["children"][0]["style"]["color"] == "#FF0000"


def test_validation_errors():
    schema = blank_schema("Test")
    home = schema["screens"][0]
    root = home["root"]["id"]
    cases = [
        ("add_components", {"screen_id": "nope", "parent_id": root, "components": [{"type": "Text"}]}, "Unknown screen_id"),
        ("add_components", {"screen_id": home["id"], "parent_id": root, "components": [{"type": "Text", "children": [{"type": "Text"}]}]}, "cannot have children"),
        ("add_components", {"screen_id": home["id"], "parent_id": root, "components": [{"type": "Text", "props": {"label": "x"}}]}, "has no prop"),
        ("add_components", {"screen_id": home["id"], "parent_id": root, "components": [{"type": "Blink"}]}, "Invalid input"),
        ("add_components", {"screen_id": home["id"], "parent_id": root, "components": [{"type": "Text", "style": {"color": "red"}}]}, "hex color"),
        ("add_components", {"screen_id": home["id"], "parent_id": root, "components": [{"type": "Text"}, {"type": "AppBar"}]}, "AppBar"),
        ("set_navigation", {"type": "tabs", "initial_screen_id": home["id"], "tabs": [{"screen_id": home["id"], "label": "Home", "icon": "home"}]}, "2 to 5"),
        ("delete_screen", {"screen_id": home["id"]}, "at least one screen"),
    ]
    for name, args, message in cases:
        with pytest.raises(ToolError, match=message):
            run(schema, name, args)
    assert home["root"]["children"] == []  # failed calls change nothing


def test_delete_screen_cleans_references():
    schema = blank_schema("Test")
    home = schema["screens"][0]
    other = run(schema, "create_screen", {"name": "Other"}).result
    run(schema, "add_components", {"screen_id": home["id"], "parent_id": home["root"]["id"], "components": [
        {"type": "Button", "on_tap": {"type": "navigate", "screenId": other["screen_id"]}}]})
    run(schema, "set_navigation", {"type": "tabs", "initial_screen_id": home["id"], "tabs": [
        {"screen_id": home["id"], "label": "Home", "icon": "home"}, {"screen_id": other["screen_id"], "label": "Other", "icon": "star"}]})
    run(schema, "delete_screen", {"screen_id": other["screen_id"]})
    assert "onTap" not in home["root"]["children"][0]
    assert schema["navigation"]["type"] == "stack" and schema["navigation"]["tabs"] == []


def test_move_and_models():
    schema = blank_schema("Test")
    home = schema["screens"][0]
    out = run(schema, "add_components", {"screen_id": home["id"], "parent_id": home["root"]["id"], "components": [
        {"type": "Card"}, {"type": "Text", "props": {"text": "x"}}]}).result["created"]
    card, text = out[0]["id"], out[1]["id"]
    run(schema, "move_component", {"screen_id": home["id"], "component_id": text, "new_parent_id": card})
    assert home["root"]["children"][0]["children"][0]["id"] == text
    with pytest.raises(ToolError, match="into itself"):
        run(schema, "move_component", {"screen_id": home["id"], "component_id": card, "new_parent_id": card})

    user = run(schema, "create_data_model", {"name": "User", "fields": [{"name": "email", "type": "string", "required": True}]}).result
    assert list(user["fields"]) == ["id", "email"]
    run(schema, "create_data_model", {"name": "Post", "fields": [{"name": "author", "type": "reference", "reference_model_id": user["model_id"]}]})
    with pytest.raises(ToolError, match="already exists"):
        run(schema, "create_data_model", {"name": "user"})


# ─── Loop + chat endpoint with a fake OpenRouter (OpenAI-compatible) client ───


def text_of(content):
    """Message text whether it's a plain string or content parts (parts carry cache breakpoints)."""
    return content if isinstance(content, str) else "".join(p.get("text", "") for p in content)


def chunk(content=None, tool_calls=None, finish=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish)])


def call_chunks(index, id_, name, args):
    """A tool call streamed in pieces, like real providers do."""
    raw = json.dumps(args)
    half = len(raw) // 2
    return [
        chunk(tool_calls=[SimpleNamespace(index=index, id=id_, function=SimpleNamespace(name=name, arguments=raw[:half]))]),
        chunk(tool_calls=[SimpleNamespace(index=index, id=None, function=SimpleNamespace(name=None, arguments=raw[half:]))]),
    ]


def usage_chunk(prompt, completion, cached=0, cost=None):
    """The final chunk OpenRouter sends with stream_options.include_usage: no choices, just usage."""
    details = SimpleNamespace(cached_tokens=cached)
    usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, prompt_tokens_details=details, cost=cost)
    return SimpleNamespace(choices=[], usage=usage)


def turn(texts=(), calls=(), finish=None, usage=None):
    """One model turn: text pieces and tool calls as (id, name, args), optionally a usage chunk."""
    chunks = [chunk(content=t) for t in texts]
    for i, (id_, name, args) in enumerate(calls):
        chunks += call_chunks(i, id_, name, args)
    chunks.append(chunk(finish=finish or ("tool_calls" if calls else "stop")))
    if usage:
        chunks.append(usage_chunk(*usage))
    return chunks


class FakeClient:
    """Replays scripted turns and records the requests it received."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": [dict(m) for m in kwargs["messages"]]})
        chunks = self.turns.pop(0)

        async def stream():
            for c in chunks:
                yield c
        return stream()


def test_chat_endpoint_streams_and_persists(authed, monkeypatch):
    project = authed.post("/api/projects", json={"prompt": "plant app"}).json()
    home = project["schema"]["screens"][0]
    fake = FakeClient([
        turn(calls=[("t1", "set_theme", {"primary": "#2E7D32"}), ("t2", "set_theme", {"primary": "green"})]),
        turn(calls=[("t3", "add_components", {"screen_id": home["id"], "parent_id": home["root"]["id"], "components": [{"type": "Text", "props": {"text": "Plants"}}]})]),
        turn(texts=["Made it ", "green."]),
    ])
    monkeypatch.setattr(runner, "get_client", lambda: fake)

    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "Make it green", "selection": {"screenId": home["id"]}})
    assert r.status_code == 200
    events = [block.split("\n")[0].removeprefix("event: ") for block in r.text.strip().split("\n\n")]
    assert events == ["start", "change", "schema", "change", "schema", "text", "text", "done", "message"]

    # The request is OpenAI-shaped: system prompt first, tools as functions, streamed.
    first = fake.requests[0]
    assert first["model"] and first["stream"] is True
    assert first["messages"][0]["role"] == "system" and first["messages"][0]["content"][0]["cache_control"]
    assert "<selection>" in first["messages"][1]["content"][0]["text"]  # newest message carries a breakpoint
    # Later turns: breakpoints slide onto the newest tool results.
    later = fake.requests[2]["messages"]
    assert later[-1]["role"] == "tool" and later[-1]["content"][0]["cache_control"]
    assert first["tools"][0]["type"] == "function"
    assert first["extra_body"] == {"usage": {"include": True}, "reasoning": {"effort": "high"}}  # empty app -> new-app effort
    assert first["stream_options"] == {"include_usage": True}

    # Split tool-call arguments were reassembled; the invalid call went back as an error result.
    second = fake.requests[1]["messages"]
    assert second[-3]["role"] == "assistant" and [c["id"] for c in second[-3]["tool_calls"]] == ["t1", "t2"]
    assert second[-2]["tool_call_id"] == "t1" and text_of(second[-2]["content"]) == '{"ok":true}'
    assert second[-1]["tool_call_id"] == "t2" and "hex color" in text_of(second[-1]["content"])

    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert saved["schema"]["theme"]["primary"] == "#2E7D32"
    assert saved["schema"]["screens"][0]["root"]["children"][0]["props"]["text"] == "Plants"
    assistant = saved["messages"][-1]
    assert assistant["role"] == "assistant" and assistant["content"] == "Made it green."
    assert len(assistant["changes"]) == 2 and assistant["version_id"]

    # The version captured before the run restores the original theme.
    restored = authed.post(f"/api/projects/{project['id']}/versions/{assistant['version_id']}/restore").json()
    assert restored["schema"]["theme"]["primary"] == "#6750A4"


def test_invalid_tool_json_is_reported_to_the_model(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    broken = [chunk(tool_calls=[SimpleNamespace(index=0, id="b1", function=SimpleNamespace(name="set_theme", arguments='{"primary": '))]), chunk(finish="tool_calls")]
    fake = FakeClient([broken, turn(texts=["ok"])])
    monkeypatch.setattr(runner, "get_client", lambda: fake)
    authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "Invalid JSON" in text_of(fake.requests[1]["messages"][-1]["content"])


def test_chat_reports_errors(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    monkeypatch.setattr(runner, "get_client", lambda: FakeClient([turn(finish="content_filter")]))
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "event: error" in r.text and "declined" in r.text
    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert "declined" in saved["messages"][-1]["content"]


def test_openrouter_errors_are_explained(authed, monkeypatch):
    import httpx
    import openai

    project = authed.post("/api/projects", json={"name": "X"}).json()

    class OutOfCredits:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def create(self, **_):
            response = httpx.Response(402, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
            raise openai.APIStatusError("Insufficient credits", response=response, body=None)

    monkeypatch.setattr(runner, "get_client", lambda: OutOfCredits())
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "out of credits" in r.text


def test_missing_api_key_is_explained(authed, monkeypatch):
    from wolf_api import config
    project = authed.post("/api/projects", json={"name": "X"}).json()
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    runner._client = None
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "OPENROUTER_API_KEY" in r.text


def test_daily_generation_limit(authed, monkeypatch):
    from wolf_api import config
    monkeypatch.setattr(config, "DAILY_GENERATION_LIMIT", 2)
    project = authed.post("/api/projects", json={"name": "X"}).json()
    monkeypatch.setattr(runner, "get_client", lambda: FakeClient([turn(texts=["ok"]), turn(texts=["ok"])]))
    for _ in range(2):
        assert authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"}).status_code == 200
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert r.status_code == 429 and "limit of 2" in r.json()["detail"]


def test_tool_schemas_have_no_refs():
    def walk(node):
        if isinstance(node, dict):
            assert "$ref" not in node and "$defs" not in node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    for tool in tool_definitions():
        walk(tool["function"]["parameters"])


def test_runs_are_accounted(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    home = project["schema"]["screens"][0]
    fake = FakeClient([
        turn(calls=[("t1", "set_theme", {"primary": "#2E7D32"})], usage=(8000, 300, 6000, 0.0012)),
        turn(texts=["Done."], usage=(8400, 40, 8000, 0.0004)),
    ])
    monkeypatch.setattr(runner, "get_client", lambda: fake)
    authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "green"})

    runs = authed.get(f"/api/projects/{project['id']}/runs").json()
    assert len(runs) == 1
    run = runs[0]
    assert run["outcome"] == "completed" and run["turn_count"] == 2 and run["changes"] == 1
    assert (run["prompt_tokens"], run["completion_tokens"], run["cached_tokens"]) == (16400, 340, 14000)
    assert abs(run["cost_usd"] - 0.0016) < 1e-9
    assert run["model"]


def test_failed_runs_record_their_outcome(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    monkeypatch.setattr(runner, "get_client", lambda: FakeClient([turn(finish="content_filter", usage=(5000, 10))]))
    authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    run = authed.get(f"/api/projects/{project['id']}/runs").json()[0]
    assert run["outcome"] == "declined" and run["prompt_tokens"] == 5000 and run["cost_usd"] is None


def test_model_works_with_short_ids(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    fake = FakeClient([
        # The model only ever sees aliases: s1 is the Home screen, c1 its root.
        turn(calls=[("t1", "add_components", {"screen_id": "s1", "parent_id": "c1", "components": [{"type": "Text", "props": {"text": "Hi"}}]})]),
        turn(texts=["Added."]),
    ])
    monkeypatch.setattr(runner, "get_client", lambda: fake)
    authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "add a greeting"})

    first_user = text_of(fake.requests[0]["messages"][1]["content"])
    assert '"id":"s1"' in first_user
    import re
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", first_user)
    result = text_of(fake.requests[1]["messages"][-1]["content"])
    assert '"id":"c2"' in result  # the new Text got the next alias, not a UUID
    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert saved["schema"]["screens"][0]["root"]["children"][0]["props"]["text"] == "Hi"


def test_long_runs_are_compacted(authed, monkeypatch):
    from wolf_api import config
    monkeypatch.setattr(config, "COMPACT_AFTER_CHARS", 600)
    project = authed.post("/api/projects", json={"prompt": "an app with many screens"}).json()
    names = [f"Screen {i}" for i in range(8)]
    big = [{"type": "Text", "props": {"text": "x" * 120}} for _ in range(4)]
    turns = [turn(calls=[(f"c{i}", "create_screen", {"name": n})]) for i, n in enumerate(names)]
    turns.append(turn(calls=[("a1", "add_components", {"screen_id": "s1", "parent_id": "c1", "components": big})]))
    turns.append(turn(texts=["All done."]))
    fake = FakeClient(turns)
    monkeypatch.setattr(runner, "get_client", lambda: fake)
    authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "an app with many screens"})

    last = fake.requests[-1]["messages"]
    checkpoints = [m for m in last if m["role"] == "user" and "<progress>" in text_of(m["content"])]
    assert len(checkpoints) == 1
    cp = text_of(checkpoints[0]["content"])
    assert "an app with many screens" in cp and "- Created Screen 0 screen" in cp and '"name":"Screen 7"' in cp
    # The live tail is short and every tool result still follows its call.
    assert len(last) < 2 + 2 * len(turns)
    call_ids = {c["id"] for m in last if m["role"] == "assistant" for c in (m.get("tool_calls") or [])}
    assert all(m["tool_call_id"] in call_ids for m in last if m["role"] == "tool")
    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert len(saved["schema"]["screens"]) == 9 and saved["messages"][-1]["content"] == "All done."
