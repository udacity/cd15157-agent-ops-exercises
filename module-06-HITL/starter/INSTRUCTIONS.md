# Exercise: Adding Human-in-the-Loop Approvals to RealThor

**Module 6 — Human-in-the-Loop and Policies**
**Estimated Time:** 10 minutes

---

## Overview

RealThor now recommends **channel strategy** for supply opportunities: marketplace (list on MLS) or
iBuyer (direct acquisition). iBuyer decisions above a capital threshold are high-risk and
irreversible, they must pause and wait for operator approval before executing. A guardrail can't
draw that line, the recommendation isn't malicious, it's just too consequential to automate. A
*policy* draws it: it weighs the condition and decides whether to pause.

Your one job is the policy logic: `evaluate_channel_policy` in `src/realthor/policies.py`. The HITL
middleware, the action tool, and the CLI approve/reject loop are all pre-provided and call your
function through a `when` predicate.

> The question this version answers: *"Your agent can suggest, but when the stakes are high enough,
> who makes the call?"*

---

## What You Have

Everything except the policy logic is already wired:

| File | What it does |
|---|---|
| `guardrails.py` | `make_hitl_policy(cfg)` — configures `HumanInTheLoopMiddleware` with a `when` predicate that calls your `evaluate_channel_policy` |
| `tools.py` | `submit_channel_recommendation` — pure action tool, no interrupt logic |
| `agents.py` | `build_main_agent(cfg, checkpointer=None)` — HITL middleware already in the stack |
| `app.py` | `chat` command with the `--approval` flag and the interrupt/resume loop |
| `config.yaml` | `hitl.ibuyer_threshold: 500000` |
| `tests/test_policies.py` | 9 unit tests — all fail until you implement the function |
| `src/realthor/policies.py` | the `PolicyDecision` dataclass + the `evaluate_channel_policy` stub (**your deliverable**) |

> **Before you start:** copy `.env.example` to `.env`. RealThor defaults to Vocareum: keep
> `LLM_PROVIDER=vocareum` and paste your Vocareum key from the Udacity workspace. To run against
> OpenAI directly, set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`.
>
> Then: `cd realthor && uv sync`

---

## Tasks

### Task 1 — Implement `evaluate_channel_policy`

Open `src/realthor/policies.py`. `PolicyDecision` is already defined; implement the one function per
these rules:

| Input | Output |
|---|---|
| `channel == "marketplace"` | `requires_approval=False`, `risk_level="low"` |
| `channel == "ibuyer"` and `estimated_value > threshold` | `requires_approval=True`, `risk_level="high"`, `reason` includes both dollar amounts |
| `channel == "ibuyer"` and `estimated_value <= threshold` | `requires_approval=False`, `risk_level="medium"` |
| any other channel | `requires_approval=False`, `risk_level="low"` |

Format dollar amounts as `${value:,.0f}` (e.g. `$610,000`, not `610000.0`). This function is the
`when` predicate `make_hitl_policy` calls, returning `requires_approval=True` is what makes the agent
pause on a high-value iBuyer.

### Task 2 — Verify

The unit tests need no API key:

```bash
uv run pytest tests/test_policies.py -v   # 9 tests
sh ops.sh
```

Then exercise the full pause/resume flow from the terminal:

```bash
# marketplace — executes immediately, no pause
uv run realthor chat -u analyst_001 -m "Recommend marketplace channel for OPP-00001"

# high-value iBuyer, no --approval — pauses and shows the pending action
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015"

# resume with a decision
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015" --approval approve
uv run realthor chat -u analyst_001 -m "Recommend iBuyer channel for OPP-00015" --approval reject
```

### Task 3 — Commit

```bash
git add src/realthor/policies.py
git commit -m "feat: add channel-policy HITL approvals to RealThor v0.6"
```

---

## Deliverable

`src/realthor/policies.py` with `evaluate_channel_policy` implemented, all 9 policy tests passing,
and `sh ops.sh` green.

---

## Verification

```bash
sh ops.sh
# → policy tests pass, 18 integrity checks pass, eval scenarios pass

git log --oneline
# → new commit on top
```
