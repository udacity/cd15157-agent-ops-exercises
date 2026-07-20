import click
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from realthor.agents import build_agent
from realthor.config import load_config, resolve_paths

load_dotenv()

QUESTION = "Which acquisition channel should we use for 3-bedroom houses in north, marketplace or iBuyer?"


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
