# Exercise M06 — Human-in-the-Loop and Policies

## What you're building

RealThor now recommends **channel strategy** for supply opportunities: marketplace (list on MLS) or iBuyer (direct acquisition). iBuyer decisions above a capital threshold are high-risk — they must pause and wait for operator approval before executing.

Your deliverable is a single file: **`src/realthor/policies.py`**.

---

## What's pre-provided

Everything except the policy logic is already wired:

| File | What it does |
|---|---|
| `guardrails.py` | `make_hitl_policy(cfg)` — configures `HumanInTheLoopMiddleware` with a `when` predicate that calls your `evaluate_channel_policy` |
| `tools.py` | `submit_channel_recommendation` — pure action tool, no interrupt logic |
| `agents.py` | `build_main_agent(cfg, checkpointer=None)` — includes HITL middleware in the stack |
| `app.py` | `chat` command with `--approval` flag and interrupt/resume loop |
| `config.yaml` | `hitl.ibuyer_threshold: 500000` |
| `tests/test_policies.py` | 9 unit tests — all fail until you implement the function |

---

## Your task

Open `src/realthor/policies.py` and implement `evaluate_channel_policy`.

The function signature is already defined. The `PolicyDecision` dataclass is also pre-provided.

**Rules:**

| Input | Output |
|---|---|
| `channel == "marketplace"` | `requires_approval=False`, `risk_level="low"` |
| `channel == "ibuyer"` and `estimated_value > threshold` | `requires_approval=True`, `risk_level="high"`, `reason` includes both dollar amounts |
| `channel == "ibuyer"` and `estimated_value <= threshold` | `requires_approval=False`, `risk_level="medium"` |
| any other channel | `requires_approval=False`, `risk_level="low"` |

**Format dollar amounts** as `${value:,.0f}` (e.g., `$610,000`, not `610000.0`).

---

## How to verify

Run the unit tests first — they don't require an API key:

```bash
uv run pytest tests/test_policies.py -v
```

Expected: 9 tests pass.

Then run the full CI suite:

```bash
sh ops.sh
```

Then test the HITL flow manually:

```bash
# No approval needed — marketplace executes immediately
uv run realthor chat -u analyst_001 -m "Recommend marketplace channel for OPP-00001"

# High-value iBuyer — should pause and ask for approval
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015"

# Resume with approval
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015" --approval approve

# Resume with rejection
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015" --approval reject
```

---

## How it all connects

`make_hitl_policy(cfg)` in `guardrails.py` configures `HumanInTheLoopMiddleware` to watch `submit_channel_recommendation`. Before that tool executes, the `when` predicate runs:

```python
def _needs_approval(req: ToolCallRequest) -> bool:
    ...
    decision = evaluate_channel_policy(channel, estimated_value, role, threshold)
    return decision.requires_approval
```

If `requires_approval=True`, LangGraph fires `interrupt()` — execution pauses. The CLI detects `result["__interrupt__"]`, prints the pending action, and exits. The user re-runs with `--approval approve` or `--approval reject`. The graph resumes via `Command(resume={"decisions": [{"type": approval}]})`.

Your function is the only missing piece.
