# Exercise: Implement Monitoring for RealThor

## What you're building

You will implement `src/realthor/monitor.py` — a pure Python module that reads structured run logs, computes aggregate metrics, and writes a monitoring report.

Everything else is already wired. `app.py` includes `_log_run`, `_build_run_record`, and a `report` subcommand that import from `monitor.py`. Every call to `realthor chat` or `realthor analyze` appends one JSON record to `logs/runs.jsonl`. Your job is to implement the three functions that read those records, aggregate them, and produce a report.

---

## Your deliverable

One file: `src/realthor/monitor.py`.

Two dataclasses are already defined — `RunRecord` and `MonitoringMetrics`. Do not modify them. Implement these three functions:

### `load_run_records(log_path: Path) -> list[RunRecord]`

Read `logs/runs.jsonl`. Each line is a JSON object with the same fields as `RunRecord`. Return a list of `RunRecord` objects. If the file doesn't exist, return `[]`.

### `compute_metrics(records: list[RunRecord]) -> MonitoringMetrics`

Aggregate the records. Key rules:
- **p95 latency**: sort all `latency_s` values; take the value at the 95th percentile index. If fewer than 20 records, use the maximum latency as the p95 fallback.
- **tool_call_counts**: flatten all `tools_called` lists across records and count occurrences.
- **common_failure_reasons**: group non-empty `failure_reason` values by count, return the top 5 as `list[tuple[str, int]]`.

### `generate_report(metrics: MonitoringMetrics, output_dir: Path) -> None`

Write three files to `output_dir`:
- `monitoring_report.md` — a markdown table of all metrics, plus a "Key signals" section flagging any metric above its threshold (p95 latency > 5s, failure rate > 10%, avg cost per run > $0.05)
- `monitoring_report.json` — `dataclasses.asdict(metrics)` serialized as JSON
- `monitoring_report.html` — self-contained HTML with the same metrics table and a CSS bar chart of tool call distribution. Key Signals section is color-coded: green when no thresholds exceeded, amber when any threshold fires. No external dependencies — inline CSS only.

---

## Pre-provided

- `app.py` — complete. Imports `RunRecord`, `load_run_records`, `compute_metrics`, `generate_report` from `monitor.py`.
- `tests/test_monitor.py` — 9 tests, no API key needed.
- `tests/fixtures/sample_runs.jsonl` — 10 synthetic run records for unit tests.
- `logs/runs.jsonl` — 5 pre-seeded records for manual verification.
- `config.yaml` — includes `logging.log_dir`, `logging.reports_dir`, and token cost rates.

---

## How it all connects

`app.py` calls `_build_run_record()` after each agent invocation to construct a `RunRecord`. It then calls `_log_run()` to append the record as a JSON line to `logs/runs.jsonl`. Token usage is extracted using `UsageMetadataCallbackHandler` from `langchain_core.callbacks`, which aggregates tokens across all model calls in the agent loop.

Your `load_run_records` function reads those lines. Your `compute_metrics` aggregates them. Your `generate_report` writes the summary.

`monitor.py` has no LangChain imports — it's pure Python. The 9 unit tests run in under a second with no API key.

---

## Verification

```bash
# Run unit tests first — no API key needed
uv run pytest tests/test_monitor.py -v
# Expect: 9 passed

# Full suite
sh ops.sh
# Expect: 76 unit tests + 18 data integrity + eval

# Generate report from pre-seeded logs
uv run realthor report
# Expect: "Report written to reports/monitoring_report.md"
cat reports/monitoring_report.md

# Run a live query and check the log entry
uv run realthor chat -u analyst_001 -m "What is the listing priority for west/apartment/2?"
cat logs/runs.jsonl | tail -1 | python -m json.tool
```
