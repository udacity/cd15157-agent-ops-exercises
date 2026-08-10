# Exercise — Make RealThor Runs Reproducible (Debugging)

A stakeholder reported a bad iBuyer recommendation for North Ciudaty. When the team
reran the same question, RealThor answered differently, and there was no way to
inspect what the original run actually did. In this exercise you make every run
reproducible: persist its state durably, then reconstruct it on demand.

RealThor v0.7 already logs every run to `logs/runs.jsonl` and uses an in-memory
checkpointer. Your job is to upgrade the checkpointer to a durable **SqliteSaver**
and implement the **replay** logic that rebuilds a past run's execution context.

## What's already wired for you

- `app.py` — `analyze`/`chat` already build the checkpointer via `build_checkpointer`,
  key every run by `thread_id = run_id`, and print the run_id. The `replay` subcommand
  is complete and calls your `reconstruct_context`.
- `monitor.py` — `RunRecord` already carries `prompt_version` and `dataset_version`.
- `config.yaml` — `debug.state_db` path is set.
- `tests/test_replay.py` + `tests/fixtures/state.db` — a real, offline checkpoint
  fixture and 7 tests (currently failing).
- Evaluation, data integrity, and all prior tests — unchanged.

## Your tasks — implement `src/realthor/replay.py`

1. **Read** `replay.py`, `tests/test_replay.py`, and how `app.py` calls the three
   functions. Note the LangGraph checkpointer API (`SqliteSaver`, `checkpointer.list`).
2. **`build_checkpointer(cfg)`** — open `cfg["debug"]["state_db"]` as a `SqliteSaver`
   using a raw `sqlite3` connection (`check_same_thread=False`).
3. **`load_run(thread_id, checkpointer)`** — return the thread's checkpoint tuples
   oldest→newest (reverse `checkpointer.list(config)`).
4. **`reconstruct_context(run_id, checkpointer, log_path)`** — walk the newest
   snapshot's messages to recover the tool trajectory, intermediate tool outputs, and
   final answer; cross-reference the `runs.jsonl` row for `run_id` to recover the input
   and the active prompt/dataset versions; set `restored` from whether any state existed.
5. **Verify**: `sh ops.sh` (runs all unit tests incl. `test_replay.py`, data integrity,
   and the evaluation suite).

## Verify

```bash
uv sync
cp .env.example .env   # then set LLM_PROVIDER (vocareum by default) and its key
uv run pytest tests/test_replay.py -v   # 7 tests, no API key needed
sh ops.sh

# End to end
uv run realthor chat -u analyst_002 -m "Should we acquire through iBuyer in north?"
uv run realthor replay --run-id <printed run id>
```
