"""Demo 2 — Reconstructing the run.

Same non-deterministic question, now on a durable SqliteSaver keyed by run_id. The
run's state persists to state.db, so after the fact `replay` reconstructs exactly
what that run did — its tool trajectory, the intermediate values it computed, and
its final answer — even though a fresh run would answer differently.

    uv run python demo_02.py --case all
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from realthor.agents import build_agent
from realthor.config import load_config, resolve_paths
from realthor.replay import build_checkpointer, format_report, reconstruct_context

load_dotenv()

QUESTION = "Should we acquire through iBuyer in north for 3-bedroom houses?"


def _log(cfg, run_id):
    """Persist the minimal metadata replay cross-references (input + versions)."""
    log_dir = Path(cfg["logging"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": QUESTION,
        "prompt_version": Path(cfg["paths"]["prompt"]).name,
        "dataset_version": cfg["agent"]["version"],
    }
    with open(log_dir / "runs.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")


@click.command()
@click.option("--case", default="all", type=click.Choice(["run", "replay", "all"]))
def main(case):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")
    log_path = Path(cfg["logging"]["log_dir"]) / "runs.jsonl"
    state_path = Path("last_run_id.txt")

    if case in ("run", "all"):
        run_id = str(uuid.uuid4())
        checkpointer = build_checkpointer(cfg)
        agent = build_agent(cfg, checkpointer=checkpointer)
        result = agent.invoke(
            {"messages": [HumanMessage(QUESTION)]},
            config={"configurable": {"thread_id": run_id}},
        )
        _log(cfg, run_id)
        state_path.write_text(run_id)
        click.echo("=== Run ===")
        click.echo(result["messages"][-1].content)
        click.echo(f"\nRun ID: {run_id}")

    if case in ("replay", "all"):
        run_id = state_path.read_text().strip() if state_path.exists() else None
        if not run_id:
            click.echo("No run to replay — run `--case run` first.")
            return
        click.echo("\n=== Replay (reconstructed from state.db) ===")
        ctx = reconstruct_context(run_id, build_checkpointer(cfg), log_path)
        click.echo(format_report(ctx))


if __name__ == "__main__":
    main()
