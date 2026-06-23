"""M05 demo A — the static tool ceiling.

Three precomputed-score tools answer three analyst queries perfectly.
A fourth query — row-level filtering — has no matching tool and fails.

Cases:
  --case demand      Demand signals for west/apartment/2
  --case supply      Supply snapshot for north/studio/1
  --case priority    Listing priority for west/apartment/2
  --case no-tool     What % of active west listings > 45 days on market? (no tool can answer)
  --case all         Run all four cases in sequence (default)
"""
import pathlib

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from realthor.config import load_config, resolve_paths
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

CASES = {
    "demand": "How strong is demand for 2-bedroom apartments in the west region?",
    "supply": "What's the current supply situation for 1-bedroom apartments in the north region?",
    "priority": "What's the listing priority for west 2-bedroom apartments?",
    "no-tool": (
        "What percentage of active listings in the west region "
        "have been on the market for more than 45 days?"
    ),
}


def _build_agent(cfg: dict):
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    listings = pd.read_csv(cfg["paths"]["listings_data"])
    tools = make_tools(demand, supply, listings)

    with open(cfg["paths"]["prompt_bespoke"]) as f:
        system_prompt = f.read()

    return create_agent(model=model, tools=tools, system_prompt=system_prompt)


def _run_case(agent, case: str, query: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"{'=' * 60}\n")

    if case == "no-tool":
        from langgraph.errors import GraphRecursionError
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(query)]},
                config={"recursion_limit": 5},
            )
            answer = result["messages"][-1].content
            print(f"Answer:\n{answer}\n")
        except GraphRecursionError:
            print("Agent exceeded recursion limit — no tool could answer this query.\n")
            print("─" * 60)
            print("Observation: no available tool can answer this.")
            print("It needs row-level filtering across all listings,")
            print("not a precomputed segment score.")
            print("Each new query shape like this would need a new bespoke tool.")
    else:
        result = agent.invoke({"messages": [HumanMessage(query)]})
        answer = result["messages"][-1].content
        print(f"Answer:\n{answer}\n")


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
    for c, q in cases_to_run:
        _run_case(agent, c, q)

    print()


if __name__ == "__main__":
    main()
