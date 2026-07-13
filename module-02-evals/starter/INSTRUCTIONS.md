# Exercise: Evaluating RealThor

**Module 2 — Tests and Evaluation for Agents**
**Estimated Time:** 15 minutes

---

## Overview

The `realthor/` project is already set up — it's the previous module's solution upgraded to v0.2. RealThor now returns **structured output** (a Pydantic object instead of free-form text), the prompts are versioned, and the golden evaluation dataset is pre-placed at `evaluation/eval_golden_dataset.csv`.

Your goal is to answer:

> *"Can you write a prompt that beats v2 — more accurate, no regressions, at least 10 percentage points better than baseline?"*

You will write `system_prompt_v3.md`, implement the evaluation notebook, run all three versions across 20 Ciudaty scenarios, and use a decision gate to see if your prompt earns a ship decision.

---

## What You Have

```
starter/
├── INSTRUCTIONS.md
└── realthor/
    ├── pyproject.toml
    ├── .python-version
    ├── .env.example
    ├── data/
    │   ├── demand_signals.csv
    │   └── supply_snapshot.csv
    ├── prompts/
    │   ├── system_prompt_v1.md     ← baseline prompt (do not modify)
    │   ├── system_prompt_v2.md     ← first candidate, pre-written (introduces regressions)
    │   └── system_prompt_v3.md     ← you will create this
    ├── evaluation/
    │   ├── eval_golden_dataset.csv ← 20 scenarios with expected priority and action
    │   └── evaluate.ipynb          ← skeleton notebook (implement this)
    ├── realthor_v01.ipynb          ← v0.1 reference (free-form output)
    └── realthor_v02.ipynb          ← v0.2 reference (structured output)
```

> **Before you start:** copy `.env.example` to `.env`. RealThor defaults to Vocareum: keep `LLM_PROVIDER=vocareum` and paste your Vocareum key from the Udacity workspace. To run against OpenAI directly, set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`.
>
> Run the environment: `cd realthor && uv run jupyter notebook`

---

## Tasks

### Task 1 — Write `system_prompt_v3.md`

Create `realthor/prompts/system_prompt_v3.md`. This is the prompt-engineering challenge.

You saw in the demo that v2's vague qualitative constraint ("be conservative") caused the model to downgrade scenarios it shouldn't. Your v3 needs to fix that.

**Requirements:**
- Must produce the same structured fields as v2: `priority`, `demand_reasoning`, `supply_reasoning`, `recommended_action`, `confidence`
- Must not suggest iBuyer acquisition or property purchases
- **Hint:** replace qualitative language with concrete, numeric rules — the data gives you `demand_score` and `supply_score` for each segment. Define explicit thresholds for when to recommend `prioritize_new_listings`, `monitor_opportunity`, and `deprioritize`.

### Task 2 — Implement `ask_realthor()`

Open `evaluation/evaluate.ipynb` and implement `ask_realthor()`. It takes `region`, `property_type`, `bedrooms`, and `prompt`, calls `structured_llm`, and returns a `ListingRecommendation` object.

Use `build_context()` (already provided) to build the user message. Pass the system prompt as a `SystemMessage` and the context as a `HumanMessage`.

> Run the cell that loads `system_prompt_v3.md` only after you've created it in Task 1.

### Task 3 — Implement `evaluate_output()`

Implement `evaluate_output(result, row)`. It compares the structured output against the golden dataset row:

1. `result.priority == row['expected_priority']`
2. `result.recommended_action == row['expected_action']`

Return `{'passed': bool, 'priority': str, 'action': str, 'failure_reason': str}`.

### Task 4 — Run the evaluation loop

Complete the evaluation loop: iterate over all 20 scenarios and all three prompt versions (`v1`, `v2`, `v3`). Build a `results_df` with columns `scenario_id`, `prompt_version`, `passed`, `priority`, `action`, `failure_reason`.

### Task 5 — Build the comparison summary

Group `results_df` by `prompt_version`. Compute total scenarios, passed count, and pass rate. Display the summary table.

### Task 6 — Implement the decision gate

Complete the decision gate cell. For each candidate version (v2 and v3), check both conditions:
- **No regressions** (scenarios that passed in v1 but fail in the candidate)
- **≥ 10pp improvement** over v1 (`candidate_pass_rate >= v1_pass_rate + 0.10`)

Print pass rates, regressions, and the decision per candidate. Output the final shipping decision:
- `Ship v3.` / `Ship v2.` / `Do not ship. Keep v1.`

### Task 7 — Commit the evaluation suite

```bash
git add evaluation/evaluate.ipynb prompts/system_prompt_v3.md
git commit -m "eval: implement evaluation suite and add system_prompt_v3"
```

---

## Deliverable

Updated `realthor/` with:

- `prompts/system_prompt_v3.md` — your improved prompt
- `evaluation/evaluate.ipynb` — fully implemented with results and decision

---

## Verification

Run all cells in `evaluate.ipynb`. You should see:

1. A results table with `passed`, `priority`, `action`, and `failure_reason` for each scenario × version
2. A summary table with pass rate per prompt version (v1, v2, v3)
3. A printed shipping decision: `Ship v3.` / `Ship v2.` / `Do not ship. Keep v1.`

If your v3 is rejected, look at the failure reasons in the results table and iterate on your prompt.

Then confirm the commit:

```bash
git log --oneline
```
