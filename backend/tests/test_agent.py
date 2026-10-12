from types import SimpleNamespace

import pytest

from wolf_api.agent import runner
from wolf_api.agent.tools import ToolError, execute, tool_definitions
from wolf_api.schema import blank_schema


def run(schema, name, args):
    return execute(schema, name, args)


# ─── Tools ───────────────────────────────────────────────────────────────────


def test_tool_definitions_are_well_formed():
    defs = tool_definitions()
    assert len({d["name"] for d in defs}) == len(defs)
    assert all(d["description"] and d["input_schema"]["type"] == "object" for d in defs)


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


# ─── Loop + chat endpoint with a fake Anthropic client ───────────────────────


class FakeStream:
    def __init__(self, response, texts):
        self.response, self.texts = response, texts

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for t in self.texts:
                yield t
        return gen()

    async def get_final_message(self):
        return self.response


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        content, texts, stop = self.responses.pop(0)
        return FakeStream(SimpleNamespace(content=content, stop_reason=stop), texts)


def tool_use(id_, name, input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def test_chat_endpoint_streams_and_persists(authed, monkeypatch):
    project = authed.post("/api/projects", json={"prompt": "plant app"}).json()
    home = project["schema"]["screens"][0]
    fake = FakeClient([
        ([tool_use("t1", "set_theme", {"primary": "#2E7D32"}), tool_use("t2", "set_theme", {"primary": "green"})], [], "tool_use"),
        ([tool_use("t3", "add_components", {"screen_id": home["id"], "parent_id": home["root"]["id"], "components": [{"type": "Text", "props": {"text": "Plants"}}]})], [], "tool_use"),
        ([SimpleNamespace(type="text", text="Done!")], ["Made it ", "green."], "end_turn"),
    ])
    monkeypatch.setattr(runner, "get_client", lambda: fake)

    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "Make it green", "selection": {"screenId": home["id"]}})
    assert r.status_code == 200
    events = [block.split("\n")[0].removeprefix("event: ") for block in r.text.strip().split("\n\n")]
    assert events == ["start", "change", "schema", "change", "schema", "text", "text", "done", "message"]

    # The invalid call went back to the model as an error alongside the valid one.
    results = fake.requests[1]["messages"][-1]["content"]
    assert [x.get("is_error", False) for x in results] == [False, True]
    assert "<selection>" in fake.requests[0]["messages"][0]["content"]
    assert fake.requests[0]["output_config"] == {"effort": "high"}  # empty app -> new-app effort

    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert saved["schema"]["theme"]["primary"] == "#2E7D32"
    assert saved["schema"]["screens"][0]["root"]["children"][0]["props"]["text"] == "Plants"
    assistant = saved["messages"][-1]
    assert assistant["role"] == "assistant" and assistant["content"] == "Made it green."
    assert len(assistant["changes"]) == 2 and assistant["version_id"]

    # The version captured before the run restores the original theme.
    restored = authed.post(f"/api/projects/{project['id']}/versions/{assistant['version_id']}/restore").json()
    assert restored["schema"]["theme"]["primary"] == "#6750A4"


def test_chat_reports_errors(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()
    monkeypatch.setattr(runner, "get_client", lambda: FakeClient([([], [], "refusal")]))
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "event: error" in r.text and "declined" in r.text
    saved = authed.get(f"/api/projects/{project['id']}").json()
    assert "declined" in saved["messages"][-1]["content"]


def test_missing_api_key_is_explained(authed, monkeypatch):
    project = authed.post("/api/projects", json={"name": "X"}).json()

    class NoKey:
        beta = SimpleNamespace(messages=SimpleNamespace(stream=lambda **_: (_ for _ in ()).throw(TypeError("no auth"))))

    monkeypatch.setattr(runner, "get_client", lambda: NoKey())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert "ANTHROPIC_API_KEY" in r.text


def test_daily_generation_limit(authed, monkeypatch):
    from wolf_api import config
    monkeypatch.setattr(config, "DAILY_GENERATION_LIMIT", 2)
    project = authed.post("/api/projects", json={"name": "X"}).json()
    done = [SimpleNamespace(type="text", text="ok")]
    monkeypatch.setattr(runner, "get_client", lambda: FakeClient([(done, ["ok"], "end_turn")] * 2))
    for _ in range(2):
        assert authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"}).status_code == 200
    r = authed.post(f"/api/projects/{project['id']}/chat", json={"prompt": "x"})
    assert r.status_code == 429 and "limit of 2" in r.json()["detail"]
