"""Demo 2 — The trace.

Same North iBuyer question, now with a Langfuse CallbackHandler attached to the invoke.
The handler records a span tree — one span per model call and tool call — and ships it to
Langfuse. Open the run in the UI (http://localhost:3000 for the local stack) and the
reasoning path is finally visible: the sequential tool spans get_demand_score →
get_supply_snapshot → recommend_channel, each with the values it returned, showing the low
demand score was fetched but not weighted in the decision.

Requires a Langfuse backend and LANGFUSE_* keys in .env (see LANGFUSE.md).

    uv run python demo_02.py --case traced-run
"""

import uuid

import click
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from realthor.agents import build_agent
from realthor.config import load_config, resolve_paths
from realthor.replay import build_checkpointer
from realthor.tracing import build_tracer, flush_tracer

load_dotenv()

QUESTION = "Should we acquire through iBuyer in north for 3-bedroom houses?"


@click.command()
@click.option("--case", default="traced-run", type=click.Choice(["traced-run"]))
def main(case):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")

    tracer = build_tracer(cfg)
    if tracer is None:
        click.echo("Tracing is off or unconfigured.")
        click.echo("Set tracing.enabled: true and put LANGFUSE_* keys in .env (see LANGFUSE.md).")
        return

    run_id = str(uuid.uuid4())
    agent = build_agent(cfg, checkpointer=build_checkpointer(cfg))
    try:
        result = agent.invoke(
            {"messages": [HumanMessage(QUESTION)]},
            config={
                "configurable": {"thread_id": run_id},
                "callbacks": [tracer],
                # Tags make this run easy to find and filter in the Langfuse UI.
                "metadata": {"langfuse_tags": ["demo", "north-ibuyer"]},
            },
        )
        click.echo("=== Traced run ===")
        click.echo(result["messages"][-1].content)
    finally:
        # Flush before the process exits, or the batched spans never reach Langfuse.
        flush_tracer(tracer)

    click.echo(f"\nRun ID: {run_id}")
    click.echo("Trace sent to Langfuse — open http://localhost:3000 and inspect the span tree.")


if __name__ == "__main__":
    main()
