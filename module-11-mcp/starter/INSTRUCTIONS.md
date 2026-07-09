# Exercise — Connect RealThor to its tools over MCP

RealThor has grown into a system that must reach *other* systems. Until now its market-data
tools lived inside its own process. In this exercise they move out: a **separate MCP server**
publishes them, and RealThor consumes them over the **Model Context Protocol** — becoming a
client of a standard tool service instead of hard-wiring its own tools.

Almost everything is built for you. Your job is the one connection point that makes RealThor an
MCP client.

## Two projects

```
starter/
├── mcp/         # the market-data service (an MCP server) — COMPLETE, you just run it
└── realthor/    # the interactive agent (an MCP client) — you implement ONE function
```

## Prerequisites

In `realthor/`, copy `.env.example` to `.env` and add your key:

```
LLM_PROVIDER=vocareum
VOCAREUM_API_KEY=voc-...
OPENAI_API_KEY=sk-...
# optional, for tracing:
# LANGFUSE_PUBLIC_KEY=... / LANGFUSE_SECRET_KEY=... / LANGFUSE_HOST=...
```

Install both projects:

```sh
cd mcp && uv sync && cd ..
cd realthor && uv sync && cd ..
```

## What's already wired for you

- **`mcp/` (the whole project)** — a FastMCP server publishing `get_demand_signals`,
  `get_supply_snapshot`, and `get_listing_velocity`. Start it with `uv run proptech-mcp serve`. Don't edit it.
- **`realthor/`** — the entire interactive app: login (`auth.py`), owned sessions
  (`sessions.py`), the menu (`interactive.py`), guardrails + HITL (`guardrails.py`), tracing,
  and the async turn (`app.py`). `agents.py` already knows how to build the agent from
  MCP-served tools; the interactive app already calls `load_mcp_tools` at startup.
- **`realthor/tests/test_mcp.py`** — offline tests for your deliverable. They fail until you
  implement `load_mcp_tools`; everything else passes.

## Your task — implement one function

Open **`realthor/src/realthor/mcp_client.py`** and implement `load_mcp_tools(cfg)`:

1. Read `cfg["mcp"]`; normalize the transport (`"streamable-http"` → `"streamable_http"`).
2. Build the per-server config under the key `"proptech-data"` (HTTP → `url`; stdio →
   `command` + `args`).
3. Construct a `MultiServerMCPClient({"proptech-data": <config>})`.
4. `return await client.get_tools()`.

That's the connection: RealThor's data tools now come dynamically from the MCP server.

## Verify

```sh
# the deliverable's tests (offline, no server needed)
cd realthor && uv run pytest tests/test_mcp.py -v

# the full check
sh ops.sh

# end to end — start the server, then log in and ask
cd ../mcp && uv run proptech-mcp serve          # terminal 1
cd ../realthor && uv run realthor      # terminal 2 → analyst_001 / realthor-dev → New session
#   ask: "What is the demand score for a 2-bedroom apartment in the west region?"
```

The answer comes from a tool running in the `mcp/` process, over the protocol. Kill the server
and ask again — the call fails, proving the tools are truly remote.
