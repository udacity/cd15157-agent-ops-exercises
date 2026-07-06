"""Demo 1 — The failure that won't reproduce.

RealThor on an in-memory checkpointer (M07 behavior). The North iBuyer question is
non-deterministic: rerun it and the recommendation can change. And because state
lives only in memory, once the process exits there is no way to ask "what did the
first run actually do?" — no trajectory, no intermediate values, nothing to inspect.

    uv run python demo_01.py --case all
"""

import click
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from realthor.agents import build_agent
from realthor.config import load_config, resolve_paths

load_dotenv()

QUESTION = "Should we acquire through iBuyer in north for 3-bedroom houses?"


def _run_once(agent, thread_id):
    result = agent.invoke(
        {"messages": [HumanMessage(QUESTION)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


@click.command()
@click.option("--case", default="all",
              type=click.Choice(["first-run", "rerun", "diff", "all"]))
def main(case):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")
    agent = build_agent(cfg, checkpointer=InMemorySaver())

    if case in ("first-run", "all"):
        click.echo("=== First run ===")
        click.echo(_run_once(agent, "run-1"))

    if case in ("rerun", "diff", "all"):
        click.echo("\n=== Rerun (same question, fresh thread) ===")
        click.echo(_run_once(agent, "run-2"))

    if case in ("diff", "all"):
        click.echo("\n--- The problem ---")
        click.echo("The two answers can differ, and neither run left anything behind.")
        click.echo("InMemorySaver state is gone with the process — there is no run to inspect.")


if __name__ == "__main__":
    main()
