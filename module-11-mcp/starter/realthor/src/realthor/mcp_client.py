"""Connect RealThor to the MCP data service — YOUR deliverable.

RealThor no longer builds its market-data tools in-process. It fetches them from
the running MCP server (the `mcp/` project) over the Model Context Protocol, so
the exact same tools are callable by any MCP client. The rest of the app treats
whatever this returns like any other tool list — this one function is the whole
connection.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient


async def load_mcp_tools(cfg: dict) -> list:
    """Build the MCP client from config and return the server's tools.

    TODO: implement this. Steps:
      1. Read ``cfg["mcp"]``. Normalize the transport name for the adapter:
         ``cfg["mcp"]["transport"].replace("-", "_")`` (e.g. "streamable-http"
         → "streamable_http").
      2. Build the per-server config dict under the key ``"proptech-data"``:
           * HTTP:  {"transport": <transport>, "url": cfg["mcp"]["url"]}
           * stdio: {"transport": "stdio", "command": cfg["mcp"]["command"],
                     "args": cfg["mcp"]["args"]}
      3. Construct ``MultiServerMCPClient({"proptech-data": <server config>})``.
      4. ``return await client.get_tools()`` — MCP tools mapped to LangChain tools.

    Run ``uv run proptech-mcp serve`` in the ``mcp/`` project first, then launch RealThor.
    """
    raise NotImplementedError("Implement load_mcp_tools — connect RealThor to the MCP data service.")
