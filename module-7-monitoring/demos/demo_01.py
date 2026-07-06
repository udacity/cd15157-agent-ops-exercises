"""M07 demo 01 — RealThor without monitoring.

Four varied cases run and scroll by in the terminal. No logs written.
The team cannot answer: how many succeeded? what did each cost? which
tools were called? was there a guardrail block?

Cases:
  --case normal      Listing priority query (tools: get_listing_priority)
  --case blocked     Input guardrail fires — executive compensation query
  --case hitl        iBuyer recommendation above threshold — HITL interrupt
  --case multi-tool  Cross-segment comparison — multiple tool calls
  --case all         Run all four cases in sequence (default)
"""

import pathlib
import uuid

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt.tool_node import ToolCallRequest

from realthor.config import load_config, resolve_paths
from realthor.policies import evaluate_channel_policy
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

BLOCKED_TERMS = [
    "executive compensation",
    "layoff",
    "acquisition target",
    "m&a",
]

CASES = {
    "normal": {
        "query": "What's the listing priority for west/apartment/2?",
        "approval": None,
    },
    "blocked": {
        "query": "What are the executive compensation packages for regional managers?",
        "approval": None,
    },
    "hitl": {
        "query": (
            "Recommend an iBuyer channel strategy for OPP-00015. "
            "It's a large west house. Submit the recommendation."
        ),
        "approval": None,
    },
    "multi-tool": {
        "query": (
            "Compare listing priority for west/apartment/2 and north/apartment/2. "
            "Which region has stronger demand?"
        ),
        "approval": None,
    },
}


def _check_input(message: str) -> str | None:
    lower = message.lower()
    for term in BLOCKED_TERMS:
        if term in lower:
            return term
    return None


def _make_hitl_policy(cfg: dict) -> HumanInTheLoopMiddleware:
    threshold = cfg["hitl"]["ibuyer_threshold"]
    opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])

    def _needs_approval(req: ToolCallRequest) -> bool:
        channel = req.tool_call["args"].get("channel", "")
        opp_id = req.tool_call["args"].get("opportunity_id", "")
        row = opps[opps["supply_opportunity_id"] == opp_id]
        estimated_value = float(row.iloc[0]["estimated_value"]) if not row.empty else 0.0
        decision = evaluate_channel_policy(
            channel=channel,
            estimated_value=estimated_value,
            role="analyst",
            threshold=threshold,
        )
        return decision.requires_approval

    return HumanInTheLoopMiddleware(
        interrupt_on={
            "submit_channel_recommendation": InterruptOnConfig(
                allowed_decisions=["approve", "reject"],
                when=_needs_approval,
            ),
        }
    )


def _build_agent(cfg: dict, checkpointer: InMemorySaver):
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    with open(cfg["paths"]["prompt"]) as f:
        system_prompt = f.read()
    tools = make_tools(cfg)
    hitl = _make_hitl_policy(cfg)
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=[hitl],
        checkpointer=checkpointer,
    )


def _run_case(agent, case: str, query: str, approval: str | None) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"{'=' * 60}\n")

    blocked_term = _check_input(query)
    if blocked_term:
        print(f"[GUARDRAIL] Input blocked: '{blocked_term}'")
        print("Agent: This topic is outside the scope of RealThor's capabilities.\n")
        return

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = agent.invoke({"messages": [HumanMessage(query)]}, config=config)

    if result.get("__interrupt__"):
        pending = result["__interrupt__"][0].value
        action = pending["action_requests"][0]
        print(f"[INTERRUPT] Pending approval: {action['name']}")
        print(f"[INTERRUPT] {action['description']}\n")
        print("Action requires approval. Stopping here for the demo.\n")
        return

    print(f"Agent:\n{result['messages'][-1].content}\n")


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
    checkpointer = InMemorySaver()
    agent = _build_agent(cfg, checkpointer)

    cases_to_run = list(CASES.items()) if case == "all" else [(case, CASES[case])]
    for c, info in cases_to_run:
        _run_case(agent, c, info["query"], info["approval"])

    print("\n" + "─" * 60)
    print("Four cases ran. Questions the team cannot answer:")
    print("  How many succeeded?  What was the average latency?")
    print("  Which tools were called?  How much did this cost?")
    print("  Which case triggered the guardrail?")
    print("  Answer: whatever scrolled past in the terminal.")
    print()


if __name__ == "__main__":
    main()
