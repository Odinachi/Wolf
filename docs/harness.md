# The agent harness

Wolf's AI agent is built around one idea from
[The Harness Effect](https://arxiv.org/abs/2607.06906) (Writer, 2026): for an agent, the
orchestration loop, not the model, sets most of the token bill. Swapping only the harness cut cost per
task by 41% and tokens by 38% at the same quality in that paper, and small, cheap models gained the
most. Wolf runs on a small model (Claude Haiku 5.5 by default), so the harness is where cost is won.

The code lives in [`backend/src/wolf_api/agent/`](../backend/src/wolf_api/agent).

## How a request runs

1. The user's prompt, a snapshot of the project and the selected element go to the model with 14
   schema-editing tools (`create_screen`, `add_components`, `set_theme`, `get_screen`, …).
2. The model calls tools; each call is validated against the live schema before anything changes,
   and errors go back to the model so it can fix and retry.
3. After each batch the updated schema streams to the browser and is saved.
4. The loop ends when the model replies in plain text, or a typed stop condition is hit.

## Mechanisms

| Mechanism | What Wolf does | Where |
|-----------|----------------|-------|
| **Per-task accounting** | Every turn records prompt, completion and cached tokens, OpenRouter's cost and wall-clock time. Each run is saved with its typed outcome and listed at `GET /api/projects/{id}/runs`. | `accounting.py` |
| **Cache-shape discipline** | The run's transcript is append-only, so it is a byte-stable prefix. Breakpoints sit after the tools and system prompt and slide along the two newest turns (placed on the request copy, never stored). | `context.py` |
| **Context offload** | Large projects are sent as an outline (ids, types, labels); `get_screen` fetches a screen in full on demand; the selected screen stays in full. | `context.py`, `tools.py` |
| **Short ids** | The model sees per-run aliases (`s1`, `c4`, `m1`, `f2`) instead of UUIDs, which were ~40% of the snapshot and tokenize poorly. Aliases in id fields are translated back before tools run. | `aliases.py` |
| **Structured compaction** | Past `WOLF_COMPACT_AFTER_CHARS`, older turns fold into a checkpoint: the request verbatim, a fresh snapshot and the list of changes. The schema is the durable memory, so this is deterministic and needs no extra model call. | `context.py` |
| **Failure-spend governance** | Failures are classified before deciding. Transient ones retry with backoff (honoring `Retry-After`); whitelisted ones fall through to `WOLF_FALLBACK_MODELS`; permanent ones stop. Broken streams are discarded attempts (tools only run from complete responses). A circuit breaker stops identical failing calls on the third try. | `failures.py`, `runner.py` |
| **Model-agnostic floor** | One code path for every model: `$ref`-free tool schemas, recovery of double-encoded or fenced arguments, at most 12 calls per turn, capped error messages, a hint when output was cut off. | `tools.py`, `failures.py` |

Not adopted: sub-agent delegation. The paper finds it only pays off on the strongest models, and the
model is a configuration value here. Zero-token waiting doesn't apply: Wolf runs never wait on people.

Typed run outcomes: `completed`, `stopped`, `declined`, `output_limit`, `max_turns`, `doom_loop`,
`rate_limit`, `provider_outage`, `timeout`, `connection`, `malformed_stream`, `auth`, `credits`,
`model_unavailable`, `bad_request`, `missing_key`, `crash`.

## Settings

| Variable | Default | |
|----------|---------|---|
| `WOLF_MODEL` | `anthropic/claude-haiku-5.5` | Any tool-capable OpenRouter model |
| `WOLF_FALLBACK_MODELS` | | Comma-separated fallback route |
| `WOLF_SNAPSHOT_BUDGET_CHARS` | `12000` | Above this, the project is sent as an outline |
| `WOLF_COMPACT_AFTER_CHARS` | `40000` | Transcript size that triggers compaction |
| `WOLF_MAX_AGENT_TURNS` | `30` | Hard cap on model turns per request |
| `WOLF_REASONING` | `on` | Send a reasoning effort (high for new apps, medium for edits) |

## Measuring changes: evals and release gates

[`backend/evals`](../backend/evals) holds six locked tasks: a small new app, a 10-screen app and four
edits on a seeded app. Each run reports quality (structural checks), cost per task, tokens, cache hit
rate, turns, latency, quality per dollar and completions per million tokens.

```bash
cd backend
uv run python -m evals.run --save-baseline            # freeze a baseline
uv run python -m evals.run --baseline evals/baseline.json   # fails if cost/task rises >10% or quality drops
```

Every run spends real tokens. Run it before changing prompts, tools, models or orchestration.
