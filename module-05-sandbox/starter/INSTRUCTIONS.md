# Exercise: Adding Sandboxed Code Execution to RealThor

**Module 5 — Sandboxed Code Execution**
**Estimated Time:** 15 minutes

---

## Overview

RealThor's static tools answer a finite set of query shapes. Open-ended analytical questions ("what
percent of active west listings have sat over 45 days?") don't map to any precomputed score, they
need code run against the raw data. Code execution closes that gap, but the same tool that writes a
pandas aggregation can also write `open('/etc/passwd').read()`. The boundary has to be enforced by
the execution environment, not the model.

Your one job is to implement that environment: the two functions in `src/realthor/sandbox.py`. The
analyst sub-agent that calls the sandbox, the `execute_python` tool, and the CLI are all pre-provided.

> The question this version answers: *"How do you give an agent the ability to write its own analysis
> without giving it access to everything else?"*

---

## What You Have

```
realthor/
├── src/realthor/
│   ├── sandbox.py      ← YOU implement validate_code + run_sandboxed
│   ├── agents.py       ← pre-provided (analyst sub-agent + analyze_data wiring)
│   ├── app.py          ← pre-provided (CLI)
│   ├── tools.py        ← pre-provided (execute_python calls your sandbox)
│   ├── guardrails.py   ← pre-provided
│   └── config.py       ← pre-provided
├── tests/test_sandbox.py  ← pre-provided (9 tests; 8 fail until the sandbox is done)
├── evaluation/         ← pre-provided (90 scenarios incl. sandbox S001–S010, never hand-edit)
├── data/, data_forge/, prompts/, config.yaml, ops.sh
```

`sandbox.py` already defines the `BLOCKED_IMPORTS` and `BLOCKED_BUILTINS` constants and full
docstrings for both functions. You fill in the two bodies.

> **Before you start:** copy `.env.example` to `.env`. RealThor defaults to Vocareum: keep
> `LLM_PROVIDER=vocareum` and paste your Vocareum key from the Udacity workspace. To run against
> OpenAI directly, set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`.
>
> Then: `cd realthor && uv sync`

---

## Tasks

### Task 1 — Implement the sandbox

Open `src/realthor/sandbox.py` and implement its two functions (follow the docstrings):

**`validate_code(code)` — AST validation (Layer 1).** Parse with `ast.parse` (guard `SyntaxError`),
then `ast.walk` the tree. Reject any `ast.Import`/`ast.ImportFrom` whose module root is in
`BLOCKED_IMPORTS`, and any `ast.Call` whose function name is in `BLOCKED_BUILTINS`. Return
`(False, "<reason>")` on the first match, `(True, "")` if clean.

**`run_sandboxed(code, dataframes, timeout)` — restricted execution (Layer 2).** Build `safe_globals`
with `"__builtins__": {}`, `pd`, `math`, a `print` that writes to a `StringIO` buffer, and the
injected `dataframes`. Run `exec` inside a `ThreadPoolExecutor` capped by `future.result(timeout=...)`;
call `executor.shutdown(wait=False)` in the handlers so an infinite loop can't block the main thread.
Return `(stdout, "")`, `("", "execution timed out")`, or `("", str(exc))`.

Verify as you go:

```bash
uv run pytest tests/test_sandbox.py -v
```

### Task 2 — Verify

```bash
sh ops.sh
```

Sandbox tests pass, 18 data integrity checks pass, and the sampled eval scenarios pass. Then run a
live analytical query, which the main agent delegates to the sandboxed analyst:

```bash
uv run realthor chat -u analyst_001 -m "What percentage of active west listings have been on market over 45 days?"
```

### Task 3 — Commit

```bash
git add src/realthor/sandbox.py
git commit -m "feat: add sandboxed code execution to RealThor v0.5"
```

---

## Deliverable

`src/realthor/sandbox.py` with `validate_code` and `run_sandboxed` implemented, all 9 sandbox tests
passing, and `sh ops.sh` green.

---

## Verification

```bash
sh ops.sh
# → sandbox tests pass, 18 integrity checks pass, eval scenarios pass

git log --oneline
# → new commit on top
```

## If the data gets corrupted

```bash
uv run python data_forge/generate_all.py
```
