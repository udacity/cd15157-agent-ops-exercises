# RealThor

Listing Supply Intelligence agent for Ciudaty PropTech — v0.2 with structured output, versioned prompts, and an evaluation suite.

## Setup

```bash
uv sync
cp .env.example .env   # add your OPENAI_API_KEY
```

Then launch Jupyter:

```bash
uv run jupyter notebook
```

## What Changed from v0.1

v0.1 (`realthor_v01.ipynb`) returns free-form text — the model writes a recommendation in natural language. That works for humans reading the output, but it breaks downstream automation: you can't reliably extract `priority` or `recommended_action` from an unstructured string.

v0.2 (`realthor_v02.ipynb`) uses LangChain's `with_structured_output()` to force the model to return a validated Pydantic object:

```python
class ListingRecommendation(BaseModel):
    priority: Literal["high", "medium", "low"]
    demand_reasoning: str
    supply_reasoning: str
    recommended_action: Literal["prioritize_new_listings", "monitor_opportunity", "deprioritize"]
    confidence: Literal["high", "medium", "low"]
```

The model still reasons in natural language — it now just returns that reasoning in a structured envelope. This makes the output machine-readable without losing interpretability.

## Prompt Versioning

Three prompt versions live in `prompts/`:

| Version | File | What it does |
|---|---|---|
| v1 | `system_prompt_v1.md` | Baseline — minimal instructions, no guardrails |
| v2 | `system_prompt_v2.md` | Adds qualitative constraint ("be conservative") — introduces regressions |
| v3 | `system_prompt_v3.md` | Candidate — replaces vague language with numeric thresholds |

Prompts are versioned files, not inline strings, so every change is tracked in git and every evaluation run references an explicit version. This is the foundation of prompt engineering discipline: you can always re-run any version against the full dataset and compare.

The key lesson from v1 → v2 → v3: qualitative instructions like "be conservative" are ambiguous. The model interprets them differently across scenarios. Replacing them with explicit numeric rules (`if demand_score > 0.75 and supply_score < 0.40`) makes behavior predictable and testable.

## Evaluation

### Golden Dataset

`evaluation/eval_golden_dataset.csv` contains 20 Ciudaty scenarios — each with a region, property type, bedroom count, expected priority, expected action, and a rationale explaining the human judgment:

```
G001,west,apartment,2,high,prioritize_new_listings,demand=0.91 supply=0.22 — strongest demand in dataset...
G002,north,apartment,1,low,deprioritize,demand=0.54 supply=0.81 — moderate demand but heavily oversupplied...
```

The dataset covers all five regions, all three property types, and a spread of demand/supply combinations — including edge cases where signals are close (borderline `medium`) and clear outliers at both extremes.

### Evaluation Notebook

`evaluation/evaluate.ipynb` runs all three prompt versions against all 20 scenarios and compares them. The evaluation flow:

1. **`ask_realthor(region, property_type, bedrooms, prompt)`** — calls the structured LLM and returns a `ListingRecommendation`
2. **`evaluate_output(result, row)`** — checks `result.priority == expected_priority` and `result.recommended_action == expected_action`; returns pass/fail + failure reason
3. **Evaluation loop** — iterates all 20 scenarios × 3 prompt versions; builds `results_df`
4. **Summary table** — groups by `prompt_version`, computes pass rate per version
5. **Decision gate** — applies two ship conditions per candidate version (v2, v3)

### Decision Gate

A prompt version ships only if it passes both conditions against the baseline (v1):

```
1. No regressions — it must not fail any scenario that v1 passed
2. ≥ 10pp improvement — pass_rate(candidate) >= pass_rate(v1) + 0.10
```

The gate outputs one of:

```
Ship v3.
Ship v2.
Do not ship. Keep v1.
```

If v3 is rejected, the failure reasons in `results_df` tell you exactly which scenarios failed and why — use them to iterate on the prompt.

### Running the Evaluation

Open `evaluate.ipynb` and run all cells. Expected output:

- A per-scenario results table (20 rows × 3 prompt versions = 60 rows) with `passed`, `priority`, `action`, `failure_reason`
- A summary table with pass rate per version — v2 should underperform v1 on some scenarios; v3 should exceed v1 by at least 10pp
- A printed shipping decision

## Project Structure

```
realthor/
├── pyproject.toml              ← deps: langchain, langchain-openai, ipykernel, pandas
├── .python-version             ← Python 3.12
├── .env.example                ← copy to .env, add OPENAI_API_KEY
├── data/
│   ├── demand_signals.csv      ← demand index per region/type/bedrooms
│   └── supply_snapshot.csv     ← active listing counts per segment
├── prompts/
│   ├── system_prompt_v1.md     ← baseline (do not modify)
│   ├── system_prompt_v2.md     ← first candidate (pre-written, introduces regressions)
│   └── system_prompt_v3.md     ← your improved prompt
├── evaluation/
│   ├── eval_golden_dataset.csv ← 20 scenarios with expected outputs
│   └── evaluate.ipynb          ← evaluation suite
├── realthor_v01.ipynb          ← free-form output reference
└── realthor_v02.ipynb          ← structured output reference
```

## Committing Your Work

```bash
git add evaluation/evaluate.ipynb prompts/system_prompt_v3.md
git commit -m "eval: implement evaluation suite and add system_prompt_v3"
git log --oneline
```
