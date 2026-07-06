# Exercise: Versioning RealThor v0.1

**Module 1 — Agentic System Reproducibility**
**Estimated Time:** 15 minutes

---

## Overview

A working notebook is already here — `realthor_v01.ipynb`. Run it and it produces a listing priority recommendation. But it's fragile: the system prompt is hardcoded inline, and the data files are sitting loose in the same folder.

Your job is to make RealThor **reproducible**: create a proper project structure with `uv`, move the data and prompt into versioned locations, and commit everything with git.

> The question RealThor answers: *"Given demand and supply signals for a region, should we prioritize new listings there?"*

---

## What You Have

```
starter/
├── INSTRUCTIONS.md
├── .env.example
├── demand_signals.csv     ← demand data for five Ciudaty segments
├── supply_snapshot.csv    ← supply data for the same five segments
└── realthor_v01.ipynb     ← working notebook with inline prompt (refactor this)
```

> **Before you start:** copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.

---

## Tasks

### Task 1 — Initialize the project with uv

From inside this folder, create a new Python project called `realthor`:

```bash
uv init realthor
cd realthor
```

Add the required dependencies:

```bash
uv add openai python-dotenv pandas ipykernel
```

Verify the environment works:

```bash
uv run jupyter notebook
```

### Task 2 — Create the project structure

Inside `realthor/`, create the `data/` and `prompts/` folders:

```
realthor/
├── pyproject.toml
├── uv.lock
├── .python-version
├── data/
├── prompts/
└── realthor_v01.ipynb   ← move your notebook here (Step 4)
```

### Task 3 — Move the datasets

Move `demand_signals.csv` and `supply_snapshot.csv` (from the starter root) into `realthor/data/`.

Update the notebook's data loading paths:
```python
demand = pd.read_csv("data/demand_signals.csv")
supply = pd.read_csv("data/supply_snapshot.csv")
```

### Task 4 — Extract the system prompt

The system prompt is currently an inline string in the notebook. Extract it:

1. Create `realthor/prompts/system_prompt.md` and paste the prompt text there
2. In the notebook, replace the inline string with a file load:

```python
with open("prompts/system_prompt.md") as f:
    SYSTEM_PROMPT = f.read()
```

3. Move the updated notebook into `realthor/realthor_v01.ipynb`

Run the notebook to verify it still produces a recommendation.

### Task 5 — Version with git

Initialize a git repository inside `realthor/` and make three commits:

```bash
git init
git add pyproject.toml uv.lock .python-version
git commit -m "scaffold: initialize realthor with uv"

git add data/
git commit -m "data: add demand and supply datasets"

git add prompts/ realthor_v01.ipynb
git commit -m "feat: add realthor v0.1 notebook with versioned prompt"
```

---

## Deliverable

A `realthor/` folder containing:

- `pyproject.toml`, `uv.lock`, `.python-version`
- `data/demand_signals.csv`, `data/supply_snapshot.csv`
- `prompts/system_prompt.md`
- `realthor_v01.ipynb` — loads the prompt from file, returns a recommendation
- Git history with at least 3 commits

---

## Verification

Open `realthor_v01.ipynb` and run all cells. You should see a recommendation with `priority`, `reasoning`, `recommended action`, and `confidence`.

Then confirm your git history:

```bash
git log --oneline
```

You should see at least 3 commits.
