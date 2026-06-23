"""M05 demo 02 — the sandbox constrains what demo_01_B could run freely.

The same queries from demo_01_B now run through execute_python (sandboxed) instead
of ShellToolMiddleware. One case shows code running safely. One shows a blocked import.
One shows a blocked builtin.

Cases:
  --case allowed    What % of active west listings > 45 days on market? (runs successfully)
  --case blocked    List files via os.listdir (BLOCKED: blocked import: os)
  --case timeout    Computation that exceeds the sandbox timeout (BLOCKED: execution timed out)
  --case all        Run all three cases in sequence (default)
"""
import pathlib
import sys

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from realthor.config import load_config, resolve_paths
from realthor.sandbox import run_sandboxed, validate_code

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

CASES = {
    "allowed": (
        "What percentage of active listings in the west region "
        "have been on the market for more than 45 days?",
        "~22% — sandbox runs the pandas code safely",
    ),
    "blocked": (
        "List all files in the current directory using Python's os module",
        "BLOCKED — import os is not allowed in the sandbox",
    ),
    "timeout": (
        "Run a computation that checks every number up to 10 billion for primality",
        "BLOCKED — execution timed out (sandbox enforces 30-second limit)",
    ),
}


def _build_execute_python_tool(cfg: dict):
    data_dir = pathlib.Path(cfg["paths"]["demand_data"]).parent
    listings = pd.read_csv(data_dir / "listings.csv")

    dataframes = {"listings": listings}
    timeout = cfg.get("sandbox", {}).get("timeout", 30)

    @tool
    def execute_python(code: str) -> str:
        """Run pandas analysis code against RealThor listing data.
        Available DataFrame: listings. No imports allowed. Use print() for output."""
        ok, reason = validate_code(code)
        if not ok:
            return f"BLOCKED: {reason}"
        output, error = run_sandboxed(code, dataframes, timeout=timeout)
        if error:
            return f"BLOCKED: {error}"
        return output or "(no output)"

    return execute_python


def _build_agent(cfg: dict):
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    with open(cfg["paths"]["prompt_sandbox"]) as f:
        system_prompt = f.read()

    execute_python = _build_execute_python_tool(cfg)
    return create_agent(model=model, tools=[execute_python], system_prompt=system_prompt)


def _run_case(agent, case: str, query: str, label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected: {label}")
    print(f"{'=' * 60}\n")

    result = agent.invoke({"messages": [HumanMessage(query)]})
    answer = result["messages"][-1].content
    print(f"Agent answer:\n{answer}\n")


@click.command()
@click.option(
    "--case",
    type=click.Choice(list(CASES.keys()) + ["all"]),
    default="all",
    show_default=True,
    help="Which demo case to run.",
)
def main(case: str) -> None:
    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    agent = _build_agent(cfg)

    cases_to_run = list(CASES.items()) if case == "all" else [(case, CASES[case])]
    for c, (q, label) in cases_to_run:
        _run_case(agent, c, q, label)

    print("\n" + "─" * 60)
    print("The sandbox runs the same pandas code — but blocks dangerous imports.")
    print("AST validation fires before execution. No shell access. No network.")
    print()


if __name__ == "__main__":
    main()
