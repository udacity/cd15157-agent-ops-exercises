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

QUESTIONS = {
    "channel": "Which acquisition channel should we use for 3-bedroom houses in north, marketplace or iBuyer?",
    "demand": "What is the current demand for 3-bedroom houses in north?",
    "supply": "What is the current supply snapshot for 3-bedroom houses in north?",
}

RUNS_FILE = Path("last_runs.json")


def _log(cfg, run_id, question):
    log_dir = Path(cfg["logging"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": question,
        "prompt_version": Path(cfg["paths"]["prompt"]).name,
        "dataset_version": cfg["agent"]["version"],
    }
    with open(log_dir / "runs.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")


def _load_runs():
    return json.loads(RUNS_FILE.read_text()) if RUNS_FILE.exists() else {}


def _run(cfg, scenario):
    question = QUESTIONS[scenario]
    run_id = str(uuid.uuid4())
    agent = build_agent(cfg, checkpointer=build_checkpointer(cfg))
    result = agent.invoke(
        {"messages": [HumanMessage(question)]},
        config={"configurable": {"thread_id": run_id}},
    )
    _log(cfg, run_id, question)
    runs = _load_runs()
    runs[scenario] = run_id
    RUNS_FILE.write_text(json.dumps(runs))
    click.echo(f"=== Run [{scenario}] ===")
    click.echo(result["messages"][-1].content)
    click.echo(f"\nRun ID: {run_id}")


def _replay(cfg, scenario):
    run_id = _load_runs().get(scenario)
    if not run_id:
        click.echo(f"No run to replay for '{scenario}' — run `--scenario {scenario} --case run` first.")
        return
    log_path = Path(cfg["logging"]["log_dir"]) / "runs.jsonl"
    click.echo(f"\n=== Replay [{scenario}] (reconstructed from state.db) ===")
    ctx = reconstruct_context(run_id, build_checkpointer(cfg), log_path)
    click.echo(format_report(ctx))


@click.command()
@click.option("--scenario", default="all", type=click.Choice(list(QUESTIONS) + ["all"]))
@click.option("--case", default="all", type=click.Choice(["run", "replay", "all"]))
def main(scenario, case):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")
    scenarios = list(QUESTIONS) if scenario == "all" else [scenario]
    for s in scenarios:
        if case in ("run", "all"):
            _run(cfg, s)
        if case in ("replay", "all"):
            _replay(cfg, s)


if __name__ == "__main__":
    main()
