"""M05 demo B — the analyst sub-agent as text2pandas solution.

The same failing query from demo_01_A now works. RealThor delegates to a
dedicated analyst sub-agent that writes and runs pandas code via ShellToolMiddleware.

Cases are loaded from eval_cases.json. Each case prints the query, the expected
result (ground truth from raw data), and the agent's answer side by side.

  --case pct-stale     What % of active west listings > 45 days on market?
  --case slowest-type  Which property type has the highest avg days on market?
  --case by-region     How many active listings per region, ranked?
  --case unsafe        List files via os.listdir — ShellToolMiddleware executes it (the risk)
  --case all           Run all four cases in sequence (default)
"""
import json
import pathlib
import sys

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HostExecutionPolicy, ShellToolMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from realthor.config import load_config, resolve_paths
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")
EVAL_CASES_PATH = pathlib.Path(__file__).parent / "eval_cases.json"


UNSAFE_CASE = (
    "List all files in the current directory using os.listdir",
    "directory listing — ShellToolMiddleware executes os.listdir with full host access",
)


def _load_cases() -> dict[str, tuple[str, str]]:
    """Return {case_name: (query, reference_label)} from eval_cases.json + unsafe case."""
    with open(EVAL_CASES_PATH) as f:
        rows = json.load(f)
    cases = {r["case"]: (r["query"], r["reference_label"]) for r in rows}
    cases["unsafe"] = UNSAFE_CASE
    return cases


def _build_agent(cfg: dict):
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )

    data_dir = pathlib.Path(cfg["paths"]["demand_data"]).parent

    with open(cfg["paths"]["analyst_prompt"]) as f:
        analyst_prompt = f.read()

    analyst_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=analyst_prompt,
        middleware=[
            ShellToolMiddleware(
                workspace_root=data_dir,
                execution_policy=HostExecutionPolicy(),
                startup_commands=[
                    f"export PATH={pathlib.Path(sys.executable).parent}:$PATH"
                ],
            )
        ],
    )

    @tool
    def analyze_data(question: str) -> str:
        """Use for analytical queries that require filtering or aggregating raw listing data —
        percentages, averages, rankings, counts that span many rows."""
        result = analyst_agent.invoke({"messages": [{"role": "user", "content": question}]})
        return result["messages"][-1].content

    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    listings = pd.read_csv(cfg["paths"]["listings_data"])
    bespoke_tools = make_tools(demand, supply, listings)

    with open(cfg["paths"]["prompt_analyst"]) as f:
        realthor_prompt = f.read()

    return create_agent(
        model=model,
        tools=bespoke_tools + [analyze_data],
        system_prompt=realthor_prompt,
    )


def _run_case(agent, case: str, query: str, expected: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected (from raw data): {expected}")
    print(f"{'=' * 60}\n")

    result = agent.invoke({"messages": [HumanMessage(query)]})
    answer = result["messages"][-1].content
    print(f"Agent answer:\n{answer}\n")


@click.command()
@click.option(
    "--case",
    default="all",
    show_default=True,
    help="Which demo case to run (pct-stale, slowest-type, by-region, unsafe, all).",
)
def main(case: str) -> None:
    cases = _load_cases()

    if case != "all" and case not in cases:
        raise click.BadParameter(
            f"Unknown case '{case}'. Choose from: {', '.join(cases)} or all."
        )

    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    agent = _build_agent(cfg)

    to_run = list(cases.items()) if case == "all" else [(case, cases[case])]
    for c, (q, expected) in to_run:
        _run_case(agent, c, q, expected)

    print("\n" + "─" * 60)
    print("The analyst sub-agent has one job: generate and run pandas code.")
    print("RealThor delegates to it when precomputed tools fall short.")
    print("ShellToolMiddleware provides the shell — with full host access.")
    print()


if __name__ == "__main__":
    main()
