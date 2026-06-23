# Exercise: Sandboxed Code Execution

In this exercise you will add sandboxed code execution to RealThor and wire up an analyst sub-agent that can answer open-ended analytical queries.

## What's pre-provided

- **`src/realthor/app.py`** — CLI entry point. No changes needed.
- **`src/realthor/tools.py`** — All 14 bespoke tools + `make_execute_python_tool`. The tool calls `validate_code` and `run_sandboxed` from `sandbox.py`. No changes needed once sandbox is implemented.
- **`src/realthor/guardrails.py`** — Three-layer guardrail system including the new `data_mutation_instruction` input block.
- **`src/realthor/sandbox.py`** — skeleton with `BLOCKED_IMPORTS`, `BLOCKED_BUILTINS`, and stub functions that raise `NotImplementedError`. You implement the two functions.
- **`tests/test_sandbox.py`** — 9 sandbox tests. All 8 that call `validate_code` or `run_sandboxed` will error until you implement `sandbox.py`.
- **`evaluation/eval_scenarios.csv`** — 90 scenarios including S001–S010 for the sandbox.

## What you implement

### 1. `src/realthor/sandbox.py`

Implement two functions:

**`validate_code(code: str) -> tuple[bool, str]`**
- Parse `code` with `ast.parse`
- Walk the AST with `ast.walk`
- For each `ast.Import` / `ast.ImportFrom` node, check the module root against `BLOCKED_IMPORTS`
- For each `ast.Call` node, check the function name against `BLOCKED_BUILTINS`
- Return `(False, "blocked import: <name>")` or `(False, "blocked call: <name>")` if found
- Return `(True, "")` if nothing is blocked

**`run_sandboxed(code, dataframes, timeout) -> tuple[str, str]`**
- Build `safe_globals` with `__builtins__={}`, `pd`, `math`, a `print` replacement that writes to a `StringIO` buffer, and `**dataframes`
- Run `exec(code, safe_globals)` inside a `ThreadPoolExecutor` with the given timeout
- Return `(stdout, "")` on success, `("", "execution timed out")` on timeout, `("", str(exc))` on error
- Use `executor.shutdown(wait=False)` when catching errors to avoid blocking on infinite loops

### 2. `src/realthor/agents.py`

Implement two functions:

**`build_analyst_agent(cfg)`**
- Create a `ChatOpenAI` model from cfg
- Load `analyst_prompt` from `cfg["paths"]["analyst_prompt"]`
- Build tools: `[make_execute_python_tool(cfg)]`
- Return `create_agent(model=model, tools=tools, system_prompt=analyst_prompt)`

**`build_main_agent(cfg)` — partial (just wire the analyst)**
- The TODO is inside `analyze_data`: invoke the analyst agent with the question and return the last message

## Verification

```bash
uv sync
cp .env.example .env  # add OPENAI_API_KEY

# Sandbox tests must pass first
uv run pytest tests/test_sandbox.py -v

# Then run the full check
sh ops.sh
```

When everything passes, run a live query:

```bash
uv run realthor chat -u analyst_001 -m "What percentage of active west listings have been on market over 45 days?"
```

The agent should delegate to the analyst sub-agent and return a percentage computed from `listings.csv`.
