"""A minimal RealThor agent for the demo: one scoped tool, plus the turn runner.

Intentionally simpler than the solution — one tool, no guardrail/HITL/sandbox
middleware — so the focus stays on context and state isolation. The tool reads
``runtime.context`` to scope data access to the caller; the checkpointer keys
conversation state by ``thread_id``, which is where ``thread_id_for`` plugs in.
"""

import os
import sqlite3

import pandas as pd
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from realthor import auth, sessions
from realthor.config import load_prompt, make_chat_model
from realthor.context import UserContext, thread_id_for


def build_checkpointer(cfg: dict) -> SqliteSaver:
    conn = sqlite3.connect(cfg["paths"]["state_db"], check_same_thread=False)
    return SqliteSaver(conn)


def ensure_db(cfg: dict) -> None:
    """Create + seed the application database if it is empty."""
    app_db = cfg["paths"]["app_db"]
    sessions.init_db(app_db)
    if sessions.is_empty(app_db):
        sessions.seed_users_from_csv(
            app_db, cfg["paths"]["users_data"], auth.hash_password(auth.DEV_PASSWORD)
        )


def build_agent(cfg: dict, checkpointer=None):
    model = make_chat_model(cfg)
    demand = pd.read_csv(cfg["paths"]["demand_data"])

    @tool
    def get_demand_score(
        region: str, property_type: str, bedrooms: int, runtime: ToolRuntime[UserContext]
    ) -> dict:
        """Return demand and supply scores for a market segment."""
        # Scope data access to the caller's region access.
        if not runtime.context.can_access_region(region):
            return {"status": "blocked", "reason": "region_out_of_scope", "region": region}
        row = demand[
            (demand["region"] == region)
            & (demand["property_type"] == property_type)
            & (demand["bedrooms"] == bedrooms)
        ]
        if row.empty:
            return {"status": "not_found", "region": region}
        r = row.iloc[0]
        return {
            "region": region,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "demand_score": float(r["demand_score"]),
            "supply_score": float(r["supply_score"]),
        }

    return create_agent(
        model=model,
        tools=[get_demand_score],
        system_prompt=load_prompt(cfg["paths"]["prompt"]),
        context_schema=UserContext,
        checkpointer=checkpointer,
    )


def build_tracer(cfg: dict):
    """Return a Langfuse callback handler when tracing is enabled and keys are set."""
    if not cfg.get("tracing", {}).get("enabled", False):
        return None
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def flush_tracer(tracer) -> None:
    if tracer is not None:
        from langfuse import get_client

        get_client().flush()


def run_turn_raw(agent, user_ctx, thread_id, message):
    """Pre-M10 invoke: uses a caller-supplied ``thread_id`` **directly**, with no
    identity namespacing. This is the behavior demo_01 shows failing — a fresh id
    forgets, a shared id leaks across users. The fix is ``run_turn`` below, which
    derives the thread from ``thread_id_for(user, session)``.
    """
    result = agent.invoke(
        {"messages": [HumanMessage(message)]},
        config={"configurable": {"thread_id": thread_id}},
        context=user_ctx,
    )
    return result["messages"][-1].content


def run_turn(agent, user_ctx, session_id, message, tracer=None, command="chat"):
    """Invoke one turn keyed by (identity, session). Returns the reply text.

    The thread is ``thread_id_for(user, session)`` — state resumes for the same
    identity+session and is isolated from every other. When tracing, the run is
    attributed to the user + session so traces group by identity in Langfuse.
    """
    thread_id = thread_id_for(getattr(user_ctx, "user_id", "") or "", session_id)
    callback = UsageMetadataCallbackHandler()
    callbacks = [callback] + ([tracer] if tracer else [])
    trace_meta = (
        {"metadata": {
            "langfuse_user_id": getattr(user_ctx, "user_id", "") or "guest",
            "langfuse_session_id": session_id,
            "langfuse_tags": [command],
        }}
        if tracer
        else {}
    )
    result = agent.invoke(
        {"messages": [HumanMessage(message)]},
        config={"configurable": {"thread_id": thread_id}, "callbacks": callbacks, **trace_meta},
        context=user_ctx,
    )
    flush_tracer(tracer)
    return result["messages"][-1].content
