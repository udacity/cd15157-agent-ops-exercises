"""M06 demo 01 — channel recommendations without any policy gate.

The agent can submit any channel recommendation immediately, including high-value
iBuyer acquisitions that commit significant capital. No human oversight.

Cases:
  --case marketplace    Recommend marketplace for a standard opportunity (no issue)
  --case ibuyer-small   Recommend iBuyer for a low-value opportunity (fine, below threshold)
  --case ibuyer-large   Recommend iBuyer for OPP-00015 ($610k) — executes immediately, no approval
  --case all            Run all three cases in sequence (default)
"""

import pathlib

import click
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from realthor.config import load_config, resolve_paths
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

CASES = {
    "marketplace": (
        "Recommend a marketplace channel strategy for OPP-00002. "
        "It's a standard west region property.",
        "Executes immediately — marketplace, no capital risk",
    ),
    "ibuyer-small": (
        "Recommend an iBuyer channel strategy for OPP-00001. "
        "It's a small west property priced around $190k.",
        "Executes immediately — iBuyer below threshold, no approval needed",
    ),
    "ibuyer-large": (
        "Recommend an iBuyer channel strategy for OPP-00015. "
        "It's a large west house priced at $610k. Submit the recommendation.",
        "Executes immediately — $610k iBuyer, no approval, no oversight",
    ),
}


def _build_agent(cfg: dict):
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    with open(cfg["paths"]["prompt"]) as f:
        system_prompt = f.read()
    tools = make_tools(cfg)
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)


def _run_case(agent, case: str, query: str, label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected: {label}")
    print(f"{'=' * 60}\n")

    result = agent.invoke({"messages": [HumanMessage(query)]})
    answer = result["messages"][-1].content
    print(f"Agent:\n{answer}\n")


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
    print("All recommendations executed immediately — including the $610k iBuyer.")
    print("No policy check. No approval gate. No human oversight.")
    print("Check data/channel_recommendations.jsonl to see every record written.")
    print()


if __name__ == "__main__":
    main()
