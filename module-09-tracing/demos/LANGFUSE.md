# Local Langfuse for the tracing demo

`demo_02.py` ships its span tree to Langfuse. Run Langfuse locally with its official
Docker stack, pinned to a release:

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

3. Run the traced demo and open the run in the UI:

   ```bash
   uv run python demo_02.py --case traced-run
   ```

This is a **separate** Docker stack from any RealThor container — run it from the cloned
`langfuse/` directory with its own `docker compose`. Pin the release tag; the self-hosting
stack evolves. Current quickstart: https://langfuse.com/self-hosting/deployment/docker-compose

The backend is chosen entirely by env vars, so switching to Langfuse Cloud is just a `.env`
change: set `LANGFUSE_HOST=https://us.cloud.langfuse.com` (or the EU host) and use the keys
from your cloud project.

## What to look at once it's open

After `demo_02.py` runs, go to **Tracing → Traces** and filter by the `north-ibuyer` tag.
Open the trace and read the span tree:

- **Spans** = tool calls (`get_demand_score`, `get_supply_snapshot`) — click one to see its
  input arguments and the row it returned.
- **Generations** = LLM calls — these also show the model, token counts, cost, and latency.
  The final generation is where the model turned the tool results into its recommendation.

Top to bottom, the tree is the reasoning path: what the agent fetched, in what order, and
how it decided.
