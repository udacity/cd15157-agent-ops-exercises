# Exercise: Implement Monitoring for RealThor

**Module 7 — Monitoring Agent Performance**
**Estimated Time:** 15 minutes

---

## Overview

RealThor now runs weekly across all five Ciudaty regions. It never crashes, yet its behavior drifts:
latency creeps up, token cost climbs, guardrail blocks and rejections shift week to week. None of
that shows up in a single run. It only becomes visible once you aggregate outcomes over time.

Your job is the aggregation layer: `src/realthor/monitor.py`, a pure Python module that reads the
structured run log, computes aggregate metrics, and writes a monitoring report. The logging
instrumentation and the `report` CLI command are already wired; you implement the three functions
that turn a growing JSONL log into a report the team can read at a glance.

> The question this version answers: *"Your agent isn't crashing. That's not the same as saying it's
> working."*

---

## What You Have

Everything except the three monitoring functions is already wired:

| File | What it does |
|---|---|
| `app.py` | `_log_run`, `_build_run_record`, and the `report` subcommand, all complete; every `analyze`/`chat` call appends one JSON record to `logs/runs.jsonl` |
| `monitor.py` | `RunRecord` + `MonitoringMetrics` dataclasses (do not modify) and the pre-provided `_generate_html` renderer; the three functions are your deliverable |
| `config.yaml` | `logging.log_dir`, `logging.reports_dir`, and token cost rates |
| `tests/test_monitor.py` | 9 unit tests, no API key needed, all fail until you implement the functions |
| `tests/fixtures/sample_runs.jsonl` | 10 synthetic run records for the unit tests |
| `logs/runs.jsonl` | 5 pre-seeded records for manual verification |

> **Before you start:** copy `.env.example` to `.env`. RealThor defaults to Vocareum: keep
> `LLM_PROVIDER=vocareum` and paste your Vocareum key from the Udacity workspace. To run against
> OpenAI directly, set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`.
>
> Then: `cd realthor && uv sync`

---

## Tasks

### Task 1 — Implement `monitor.py`

Open `src/realthor/monitor.py`. `RunRecord` and `MonitoringMetrics` are already defined; do not modify
them. Implement these three functions:

**`load_run_records(log_path: Path) -> list[RunRecord]`**

Read `logs/runs.jsonl`. Each line is a JSON object with the same fields as `RunRecord`. Return a list
of `RunRecord` objects. If the file does not exist, return `[]`.

**`compute_metrics(records: list[RunRecord]) -> MonitoringMetrics`**

Aggregate the records. Key rules:

- **p95 latency**: sort all `latency_s` values and take the value at the 95th percentile index. If
  fewer than 20 records, use the maximum latency as the p95 fallback.
- **tool_call_counts**: flatten all `tools_called` lists across records and count occurrences.
- **common_failure_reasons**: group non-empty `failure_reason` values by count, return the top 5 as
  `list[tuple[str, int]]`.

**`generate_report(metrics: MonitoringMetrics, output_dir: Path) -> None`**

Write three files to `output_dir`:

- `monitoring_report.md`, a markdown table of all metrics plus a "Key signals" section flagging any
  metric above its threshold (p95 latency > 5s, failure rate > 10%, avg cost per run > $0.05).
- `monitoring_report.json`, `dataclasses.asdict(metrics)` serialized as JSON.
- `monitoring_report.html`, the return value of the pre-provided `_generate_html(metrics)`. You do not
  write the HTML yourself; just call the helper and save its output.

### Task 2 — Verify

The unit tests need no API key:

```bash
uv run pytest tests/test_monitor.py -v   # 9 tests
sh ops.sh
```

Then generate a report and check a live log entry:

```bash
# Generate the report from the pre-seeded logs
uv run realthor report
cat reports/monitoring_report.md

# Run a live query and inspect the new record
uv run realthor chat -u analyst_001 -m "What is the listing priority for west/apartment/2?"
cat logs/runs.jsonl | tail -1 | python -m json.tool
```

Your report is built from your own runs, so with only a few it will be small and likely show no
signals. To see it over a realistic week, pass `--seed` from a clean log: it loads a representative
week of prior runs into an empty log so the Key Signals fire.

```bash
rm -rf logs reports
uv run realthor report --seed
cat reports/monitoring_report.md
```

### Task 3 — Commit

```bash
git add src/realthor/monitor.py
git commit -m "feat: add monitor.py with RunRecord, MonitoringMetrics, and run logging"
```

---

## Deliverable

`src/realthor/monitor.py` with `load_run_records`, `compute_metrics`, and `generate_report`
implemented, all 9 monitor tests passing, and `sh ops.sh` green.

---

## Verification

```bash
sh ops.sh
# → 74 unit tests pass, 18 integrity checks pass, eval scenarios pass

git log --oneline
# → new commit on top
```
