# Exercise — Trace RealThor's Reasoning

The team can now reproduce a run (M08 replay) but still can't see *why* the model made
its call — the reasoning path between the tool results and the decision. In this exercise
you instrument RealThor with **distributed tracing** so every run can emit a Langfuse
trace: a tree of spans for each model call and tool call.

Tracing attaches through the standard LangChain callback interface — the same
`config={"callbacks": [...]}` mechanism the usage-metadata callback already uses — so the
agent code doesn't change. You implement the small module that builds the tracer.

## Prerequisites

You have Langfuse credentials (a public key, a secret key, and a host URL). Copy
`.env.example` to `.env` and fill in:

```
OPENAI_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=...            # your Langfuse host
```

## What's already wired for you

- `app.py` — `analyze`/`chat` already have a `--trace/--no-trace` flag, build the tracer
  via `build_tracer`, splice it into the callback list, and call `flush_tracer` in
  `finally`. Nothing to change here.
- `config.yaml` — `tracing.enabled` toggle is set.
- `.env.example` — includes the `LANGFUSE_*` keys.
- `tests/test_tracing.py` — 5 unit tests (currently failing). They monkeypatch the
  Langfuse handler, so they need no network and no keys.
- `flush_tracer` in `tracing.py` — already implemented.

## Your tasks — implement `src/realthor/tracing.py`

1. **Read** `tracing.py`, `tests/test_tracing.py`, and how `app.py` calls `build_tracer`
   and `flush_tracer`. Note that the Langfuse `CallbackHandler()` takes no arguments and
   reads `LANGFUSE_*` from the environment.
2. **`build_tracer(cfg)`** — return `None` when tracing is disabled in config, or when the
   `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` env vars are missing (so the agent still
   runs, untraced). Otherwise return a `CallbackHandler()`.
3. **`trace_callbacks(cfg)`** — return `[handler]` when `build_tracer` returns a handler,
   `[]` otherwise.
4. **Verify offline**: `sh ops.sh` (runs `test_tracing.py`, data integrity, and the
   evaluation suite — no Langfuse backend needed).
5. **Verify live**: run a traced query and confirm the run appears in your Langfuse UI:

   ```bash
   uv run realthor analyze --user analyst_001 --region north --property-type house --bedrooms 3 --trace
   ```

## Understanding your trace

Open the run in Langfuse (filter by the `analyze` tag to find it). You're looking at a
**trace** — one full request, from the question to the answer. Inside is a tree of steps:

- **Spans** are the tool calls. Click `get_demand_signals` or `get_supply_snapshot` and you
  see its input (the arguments) and its output (the row it returned).
- **Generations** are the LLM calls — they also show the model, token counts, cost, and
  latency. The last generation is where the model turned the tool results into its answer.

Reading the tree top to bottom shows you exactly what the agent did and why — the reasoning
path a log or a replay can't show.

## Verify

```bash
sh ops.sh
```

All unit tests (including `test_tracing.py`), data integrity, and the evaluation suite
should pass.
