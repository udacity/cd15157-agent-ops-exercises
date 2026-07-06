# Local Langfuse for the isolation demo

`demo_02.py --trace` ships each run to Langfuse, attributed to the caller's **user** and
**session**. Run Langfuse locally with its official Docker stack, pinned to a release:

```bash
git clone --branch v3.130.0 https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d          # UI on http://localhost:3000 after ~2-3 min
```

Then:

1. Open `http://localhost:3000`, create an account (local, not the cloud), create a project.
2. Copy the project's **public** and **secret** keys into this demo's `.env`:

   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://localhost:3000
   ```

3. Run the traced demo and open the runs in the UI:

   ```bash
   uv run python demo_02.py --case login-sessions --trace
   ```

This is a **separate** Docker stack from any RealThor container — run it from the cloned
`langfuse/` directory with its own `docker compose`. Pin the release tag; the self-hosting
stack evolves. Current quickstart: https://langfuse.com/self-hosting/deployment/docker-compose

The backend is chosen entirely by env vars, so switching to Langfuse Cloud is just a `.env`
change: set `LANGFUSE_HOST=https://us.cloud.langfuse.com` (or the EU host) and use the keys
from your cloud project.

## What to look at once it's open

Go to **Tracing → Traces**. Each run carries the caller's identity:

- **Filter by User** — pick `analyst_001` and you see only that analyst's runs. A different
  user's runs are a separate, attributed group. The isolation the checkpointer enforces on
  state is now visible in the traces.
- **Filter by Session** — one session groups a user's turns together, so you can follow a
  conversation across runs (and come back to it later).
- Open a trace and read the span tree: **spans** are the `get_demand_score` tool calls
  (click one for its arguments and returned row); **generations** are the LLM calls with
  model, tokens, cost, and latency.

Attribution is set in `run_turn` via `config["metadata"]`: `langfuse_user_id`,
`langfuse_session_id`, and `langfuse_tags`.
