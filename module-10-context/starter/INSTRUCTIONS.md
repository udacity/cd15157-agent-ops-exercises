# Exercise — Scope RealThor's Context and State by Identity

RealThor now serves many people at once. Until now it trusted a `--user` flag — a *claim*,
not a login — and every run got a throwaway thread, so it couldn't hold a session and had no
way to keep one caller's state from reaching another's.

This version makes RealThor a real multi-user application: callers **log in** with a password,
work inside **owned, resumable sessions**, and every run's state is keyed to identity. Almost
all of that is already built for you. Your job is the one function the whole isolation
contract rests on: the key that ties agent state to a (user, session) pair.

## Prerequisites

Copy `.env.example` to `.env` and fill in your keys:

```
LLM_PROVIDER=vocareum
VOCAREUM_API_KEY=voc-...
OPENAI_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=...            # your Langfuse host
```

## What's already wired for you

- `auth.py` — password hashing/verification and `authenticate` (identity from the database).
- `sessions.py` — the application database (`realthor.db`): the `users` and `sessions` tables,
  session create/list/resume with ownership scoping, and LLM session titles.
- `app.py` + `interactive.py` — bare `realthor` launches the interactive app (login → menu:
  new session / resume / analyze / logout); the `analyze`/`chat` subcommands authenticate
  headlessly via `--user`/`--password`. Every turn is keyed by `thread_id_for(...)` and traces
  are attributed by user and session.
- `context.py` — `resolve_user` (identity → `UserContext` from the DB) is done. **`thread_id_for`
  and `trace_metadata` are your two TODOs.**
- `data_forge/seed_db.py` — seeds `realthor.db` from `users.csv` with a shared dev password.
- `tests/test_context.py`, `tests/test_auth.py`, `tests/test_sessions.py`,
  `tests/test_interactive.py` — offline, no API key. The `thread_id_for` + `trace_metadata`
  tests and the turn-driving CLI tests fail until you implement both functions; the rest pass.

## Your tasks — implement two functions in `src/realthor/context.py`

1. **Read** `context.py`, `tests/test_context.py`, and how `run_agent_turn` in `app.py` uses
   `thread_id_for` (to key `config={"configurable": {"thread_id": ...}}`) and `trace_metadata`
   (to attribute the Langfuse trace).
2. **Implement `thread_id_for(user_id, session_id)`** so that:
   - same `user_id` + same `session_id` → the same key (state resumes);
   - a different `user_id` *or* `session_id` → a different key (state isolated);
   - the key is **namespaced by `user_id`** (a leaked `session_id` can't cross into another
     user's checkpoint space);
   - an empty `user_id` is treated as `"guest"`.

   A simple, readable string is enough — no hashing.
3. **Implement `trace_metadata(user_ctx, session_id, command)`** — return the dict with
   `langfuse_user_id` (the user id, or `"guest"`), `langfuse_session_id`, and
   `langfuse_tags` = `[command]`. This attributes each trace to its identity and session.
4. **Verify offline**: `sh ops.sh` (unit + data integrity + evaluation). The unit/`test_context`
   steps need no backend; the **evaluation step needs your `OPENAI_API_KEY`** (only
   `test_context`/`test_auth`/`test_sessions`/`test_interactive` are fully offline).
4. **Run the app** and see isolation for yourself:

   ```bash
   uv run realthor            # log in as analyst_001 (password: realthor-dev)
                              # → New session, ask a question, exit; relaunch, Resume — it remembers.
                              # → Log in as analyst_002: their session list does NOT show analyst_001's.
   ```

## Understanding your traces

Run a traced turn and open Langfuse. Each run is attributed to the caller's **user** and
**session**: filter **by User** and you see only that identity's runs; filter **by Session** to
follow one conversation across turns. The isolation the checkpointer enforces on state is
visible in the traces — different users are different, attributed groups.

## Verify

```bash
sh ops.sh
```

All unit tests (including `test_context.py` and `test_interactive.py`), data integrity, and the
evaluation suite should pass once `thread_id_for` and `trace_metadata` are implemented.
