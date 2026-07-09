# Seeing MCP tool calls in Langfuse (optional)

The demos work without Langfuse. To *see* the MCP tool calls as spans — proving the protocol
boundary is transparent to tracing — run a local Langfuse and attach the callback.

## Local Langfuse

```sh
git clone --branch v3.130.0 https://github.com/langfuse/langfuse.git
cd langfuse && docker compose up -d      # UI on http://localhost:3000 after ~2-3 min
```

Create a project, copy its public/secret keys into `.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

## In the notebook

```python
from langfuse.langchain import CallbackHandler
handler = CallbackHandler()
result = await agent.ainvoke({"messages": [...]}, config={"callbacks": [handler]})

from langfuse import get_client
get_client().flush()     # short-lived process: flush before it exits
```

Open Langfuse → the run appears with the MCP tool calls as **spans** (args in, result out), just
like an in-process tool. Tear down with `docker compose down -v` in the `langfuse/` checkout.
