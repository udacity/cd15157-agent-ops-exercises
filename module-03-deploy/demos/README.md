# RealThor v0.3 — Demo Project

One demo video, two parts. Part 1 shows how to deploy RealThor as a CLI package. Part 2 shows RealThor as a LangChain agent with tools.

## Setup

```bash
cp .env.example .env        # add your OPENAI_API_KEY
uv sync
```

## Project Structure

```
demos/
├── realthor_v02.ipynb      ← the "before": prior version, run as a notebook
├── pyproject.toml          ← build-system, deps, CLI entry point
├── config.yaml             ← model name, temperature, file paths
├── data/
│   ├── demand_signals.csv
│   └── supply_snapshot.csv
├── prompts/
│   └── system_prompt_v3.md
└── src/
    └── realthor/
        ├── config.py       ← load_config, resolve_paths, build_context
        ├── tools.py        ← make_tools(demand, supply) → tool closures
        ├── cli.py          ← Part 1: lookup command, no model
        └── agent.py        ← Part 2: build_agent + __main__ block
```

## Part 1 — CLI with arguments and flags

```bash
uv run realthor --help
uv run realthor lookup --region west --property-type apartment --bedrooms 2
uv run realthor lookup --region south --property-type house --bedrooms 3
```

No model call. Reads CSVs, prints demand and supply data for the segment.

## Part 2 — RealThor as an agent

```bash
uv run python src/realthor/agent.py
```

The agent calls `get_demand_signals` and `get_supply_snapshot` tools, then reasons over the results using the system prompt decision framework.

To change the question, edit the `HumanMessage` in the `__main__` block of `src/realthor/agent.py`.

## Config

`config.yaml` controls the model and all file paths. No values are hardcoded in Python.

```yaml
model:
  name: gpt-4o-mini
  temperature: 0.0

paths:
  prompt: prompts/system_prompt_v3.md
  demand_data: data/demand_signals.csv
  supply_data: data/supply_snapshot.csv
```
