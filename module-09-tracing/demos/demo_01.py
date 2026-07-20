import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage

from realthor.agents import build_agent
from realthor.config import load_config, resolve_paths
from realthor.replay import build_checkpointer, format_report, reconstruct_context

load_dotenv()

QUESTION = "Should we acquire through iBuyer in north for 3-bedroom houses?"


def _log(cfg, run_id, result):
    """Write the kind of structured log line the monitoring system records per run."""
    tools = [m.name for m in result["messages"] if isinstance(m, ToolMessage) and m.name]
    log_dir = Path(cfg["logging"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": QUESTION,
        "success": True,
        "tools_called": tools,
        "prompt_version": Path(cfg["paths"]["prompt"]).name,
        "dataset_version": cfg["agent"]["version"],
    }
    with open(log_dir / "runs.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


@click.command()
@click.option("--case", default="all", type=click.Choice(["log", "replay", "all"]))
def main(case):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")
    log_path = Path(cfg["logging"]["log_dir"]) / "runs.jsonl"
    state_path = Path("last_run_id.txt")

    if case in ("log", "all"):
        run_id = str(uuid.uuid4())
        agent = build_agent(cfg, checkpointer=build_checkpointer(cfg))
        result = agent.invoke(
            {"messages": [HumanMessage(QUESTION)]},
            config={"configurable": {"thread_id": run_id}},
        )
        row = _log(cfg, run_id, result)
        state_path.write_text(run_id)
        click.echo("=== The log line (logs/runs.jsonl) ===")
        click.echo(json.dumps(row, indent=2))
        click.echo("\nThe log says a run happened, which tools it called, and that it succeeded.")

    if case in ("replay", "all"):
        run_id = state_path.read_text().strip() if state_path.exists() else None
        if not run_id:
            click.echo("No run to replay — run `--case log` first.")
            return
        click.echo("\n=== The replay (reconstructed from state.db) ===")
        ctx = reconstruct_context(run_id, build_checkpointer(cfg), log_path)
        click.echo(format_report(ctx))

    if case == "all":
        click.echo("\n--- The gap ---")
        click.echo("The log shows what happened. The replay restores the state and the values.")
        click.echo("Neither shows HOW the model weighed those values into the recommendation —")
        click.echo("the reasoning path between the tool results and the decision. That is what a")
        click.echo("trace records.")


if __name__ == "__main__":
    main()
