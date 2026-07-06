"""Distributed tracing for RealThor via Langfuse.

A trace is the ordered tree of spans — model calls, tool calls, decisions — that a
single agent invocation produces. Logs (monitor.py) tell you a run happened; replay
(replay.py) restores its state; a trace shows the *path* the reasoning took between
input and output.

Tracing attaches through the standard LangChain callback interface — the same
`config={"callbacks": [...]}` mechanism the usage-metadata callback already uses — so
the agent code is unchanged; app.py just splices the handler in at invoke time.

The backend is chosen entirely by environment variables (`LANGFUSE_HOST` + keys), so
switching between a local self-hosted Langfuse and Langfuse Cloud is a `.env` change,
not a code change.

YOUR TASK: implement build_tracer and trace_callbacks. flush_tracer is provided.
"""

import os

from langfuse import get_client
from langfuse.langchain import CallbackHandler


def build_tracer(cfg: dict):
    """Return a Langfuse CallbackHandler, or None if tracing is off/unconfigured.

    TODO 1:
      - Return None when tracing is disabled in config (cfg["tracing"]["enabled"] is
        false or missing).
      - Return None when the Langfuse credentials are absent from the environment
        (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY), so the agent still runs untraced.
      - Otherwise return CallbackHandler() — it reads LANGFUSE_* from the environment.
    """
    raise NotImplementedError("TODO 1: implement build_tracer")


def trace_callbacks(cfg: dict) -> list:
    """Return [handler] when tracing is on, [] otherwise.

    Spliceable directly into a config callback list so app.py can add tracing
    alongside the usage-metadata callback without an if-branch.

    TODO 2:
      - Call build_tracer(cfg); return [handler] if it returned a handler, else [].
    """
    raise NotImplementedError("TODO 2: implement trace_callbacks")


def flush_tracer(handler) -> None:
    """Flush batched spans before a short-lived CLI process exits.

    Langfuse ships spans asynchronously in batches; a CLI command finishes and exits
    before the batch is sent, dropping the trace. Flushing on the way out guarantees
    delivery. No-op when the run was untraced (handler is None).
    """
    if handler is not None:
        get_client().flush()
