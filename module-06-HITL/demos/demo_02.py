import pathlib
import uuid

import click
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from realthor.config import load_config, make_chat_model, resolve_paths
from realthor.policies import evaluate_channel_policy
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

CASES = {
    "marketplace": {
        "query": (
            "Recommend a marketplace channel strategy for OPP-00002. "
            "It's a standard west region property."
        ),
        "approval": None,
        "label": "No interrupt — marketplace is auto-approved",
    },
    "pending": {
        "query": (
            "Recommend an iBuyer channel strategy for OPP-00015. "
            "It's a large west house. Submit the recommendation."
        ),
        "approval": None,
        "label": "Interrupt fires — no approval provided, pauses and exits",
    },
    "approve": {
        "query": (
            "Recommend an iBuyer channel strategy for OPP-00015. "
            "It's a large west house. Submit the recommendation."
        ),
        "approval": "approve",
        "label": "Interrupt fires — approval=approve, resumes and submits",
    },
    "reject": {
        "query": (
            "Recommend an iBuyer channel strategy for OPP-00015. "
            "It's a large west house. Submit the recommendation."
        ),
        "approval": "reject",
        "label": "Interrupt fires — approval=reject, resumes and rejects",
    },
}


def _make_hitl_policy(cfg: dict) -> HumanInTheLoopMiddleware:
    threshold = cfg["hitl"]["ibuyer_threshold"]

    import pandas as pd
    opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])

    def _needs_approval(req: ToolCallRequest) -> bool:
        channel = req.tool_call["args"].get("channel", "")
        opp_id = req.tool_call["args"].get("opportunity_id", "")
        row = opps[opps["supply_opportunity_id"] == opp_id]
        estimated_value = float(row.iloc[0]["estimated_value"]) if not row.empty else 0.0
        decision = evaluate_channel_policy(
            channel=channel,
            estimated_value=estimated_value,
            role=getattr(req.runtime.context, "role", "analyst"),
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
    model = make_chat_model(cfg)
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


def _run_case(agent, case: str, query: str, approval: str | None, label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected: {label}")
    print(f"{'=' * 60}\n")

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = agent.invoke({"messages": [HumanMessage(query)]}, config=config)

    if result.get("__interrupt__"):
        pending = result["__interrupt__"][0].value
        action = pending["action_requests"][0]
        print(f"[INTERRUPT] Pending approval: {action['name']}")
        print(f"[INTERRUPT] {action['description']}\n")

        if approval is None:
            print("Action requires approval. Re-run with --approval approve or --approval reject.\n")
            return

        result = agent.invoke(
            Command(resume={"decisions": [{"type": approval}]}),
            config=config,
        )

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
        _run_case(agent, c, info["query"], info["approval"], info["label"])

    print("\n" + "─" * 60)
    print("Marketplace: auto-approved. iBuyer below threshold: auto-approved.")
    print("iBuyer above threshold: interrupted. Human decides. System resumes.")
    print("Policies are conditional. Guardrails are not.")
    print()


if __name__ == "__main__":
    main()
