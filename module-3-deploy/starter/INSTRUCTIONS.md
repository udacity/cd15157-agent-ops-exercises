# Exercise: Deploying RealThor as an Agent CLI

**Module 3 — Deploying an Agent**
**Estimated Time:** 15 minutes

---

## Overview

The `realthor/` project is already set up — it's the Module 2 solution upgraded to v0.3, using `src/` layout and LangChain. The infrastructure is pre-provided: `config.py`, `tools.py`, `config.yaml`, the versioned prompt, and all data files.

Your job is to implement `src/realthor/agent.py` — the file that wires everything together. It has two responsibilities:

1. `build_agent()` — creates a LangChain agent from config
2. `analyze` command — a click CLI command that calls the agent

When you're done:

```bash
uv run realthor analyze --region west --property-type apartment --bedrooms 2
```

should print a recommendation. And:

```bash
sh ops.sh
```

should pass all unit tests and evaluation scenarios.

---

## What You Have

```
starter/
├── INSTRUCTIONS.md
└── realthor/
    ├── pyproject.toml       ← build-system, deps, entry point (pre-configured)
    ├── config.yaml          ← model + file paths (pre-provided)
    ├── ops.sh              ← runs tests + evaluation
    ├── .env.example
    ├── data/
    │   ├── demand_signals.csv
    │   └── supply_snapshot.csv
    ├── prompts/
    │   └── system_prompt_v3.md
    ├── evaluation/
    │   ├── eval_scenarios.csv
    │   └── run_eval.py      ← evaluation script (pre-provided)
    ├── tests/
    │   ├── test_config.py   ← unit tests (pre-provided)
    │   └── test_tools.py    ← unit tests (pre-provided)
    └── src/
        └── realthor/
            ├── config.py    ← load_config, resolve_paths, build_context (pre-provided)
            ├── tools.py     ← make_tools(demand, supply) (pre-provided)
            └── agent.py     ← skeleton — implement this
```

> **Before you start:** copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
>
> Then: `cd realthor && uv sync`

---

## Tasks

### Task 1 — Explore the pre-provided infrastructure

Open `src/realthor/config.py` and read through it. Key functions:
- `load_config(config_path)` — reads `config.yaml`
- `resolve_paths(cfg, config_path)` — makes all file paths absolute (so the CLI works from any directory)
- `load_prompt(path)` — reads the markdown prompt file

Open `src/realthor/tools.py`. `make_tools(demand, supply)` takes two DataFrames and returns two tools:
- `get_demand_signals` — fetches demand data for a segment
- `get_supply_snapshot` — fetches supply data for a segment

These are **closures** — data is loaded once at startup, tools access it directly.

### Task 2 — Implement `build_agent()`

Open `src/realthor/agent.py`. Implement the `build_agent()` function:

1. Create a `ChatOpenAI` model using `cfg["model"]["name"]` and `cfg["model"]["temperature"]`
2. Load the system prompt with `load_prompt(cfg["paths"]["prompt"])`
3. Load the demand and supply DataFrames with `pd.read_csv()`
4. Call `make_tools(demand, supply)` to get the tools list
5. Return `create_agent(model=..., tools=..., system_prompt=...)`

### Task 3 — Implement the `analyze` command

In the same file, implement the `analyze` click command:

1. Call `build_agent(config_path)` to get the agent
2. Build a question string, e.g.: `f"What's the listing priority for {bedrooms}-bedroom {property_type} in the {region} region?"`
3. Call `agent.invoke({"messages": [HumanMessage(question)]})`
4. Print `result["messages"][-1].content`

### Task 4 — Run the CLI

```bash
uv run realthor --help
uv run realthor analyze --region west --property-type apartment --bedrooms 2
```

You should see the agent call the tools and return a recommendation.

### Task 5 — Run `ops.sh`

```bash
sh ops.sh
```

This runs:
1. **Unit tests** — checks that `config.py` and `tools.py` work correctly
2. **Evaluation** — runs the agent against 5 scenarios in `eval_scenarios.csv` and checks that each response contains the expected terms

All checks pass when the agent is implemented correctly. If the evaluation fails, look at the output for which terms were missing or forbidden.

### Task 6 — Commit

```bash
git add src/realthor/agent.py
git commit -m "feat: add RealThor v0.3 as agent CLI"
```

---

## Deliverable

`src/realthor/agent.py` — fully implemented with:
- `build_agent()` wiring model, prompt, tools, and `create_agent`
- `analyze` command calling the agent and printing the result

---

## Verification

```bash
uv run realthor analyze --region west --property-type apartment --bedrooms 2
# → agent calls tools, returns recommendation

sh ops.sh
# → all unit tests pass + 5/5 eval scenarios pass

git log --oneline
# → new commit on top
```
