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
