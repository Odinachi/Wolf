from wolf_api.agent.aliases import UUID, IdAliases
from wolf_api.agent.prompts import snapshot_text
from wolf_api.agent.tools import execute
from wolf_api.schema import blank_schema


def test_shorten_assigns_kind_prefixes_in_order_and_is_stable():
    schema = blank_schema("App")
    execute(schema, "create_screen", {"name": "Second"})
    execute(schema, "create_data_model", {"name": "Plant", "fields": [{"name": "name", "type": "string"}]})
    ids = IdAliases()
    text = ids.shorten(snapshot_text(schema), schema)
    assert not UUID.search(text)
    assert '"id":"s1"' in text and '"id":"s2"' in text and '"root_id":"c1"' in text and '"id":"m1"' in text and '"id":"f1"' in text
    # Same text, same bytes: the transcript prefix stays cacheable.
    assert ids.shorten(snapshot_text(schema), schema) == text


def test_expand_only_touches_id_fields():
    schema = blank_schema("App")
    ids = IdAliases()
    ids.shorten(snapshot_text(schema), schema)
    home = schema["screens"][0]
    args = {"screen_id": "s1", "parent_id": "c1", "components": [
        {"type": "Text", "props": {"text": "s1"}, "on_tap": {"type": "navigate", "screenId": "s1"}},
    ], "remove_field_ids": ["s1"], "name": "c1"}
    out = ids.expand(args)
    assert out["screen_id"] == home["id"] and out["parent_id"] == home["root"]["id"]
    assert out["components"][0]["props"]["text"] == "s1"  # free text untouched
    assert out["components"][0]["on_tap"]["screenId"] == home["id"]
    assert out["name"] == "c1"
    assert ids.expand({"screen_id": home["id"]}) == {"screen_id": home["id"]}  # real UUIDs pass through


def test_alias_savings_on_a_large_project():
    import sys
    sys.path.insert(0, "tests")
    from test_context import big_schema
    schema = big_schema(10)
    raw = snapshot_text(schema)
    short = IdAliases().shorten(raw, schema)
    assert len(short) < len(raw) * 0.7
