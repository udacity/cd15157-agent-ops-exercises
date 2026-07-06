"""M07 demo 02 — RealThor with monitoring.

Same four cases as demo_01, but now every invocation appends a structured
record to logs/runs.jsonl. After all cases, generate_report() produces
reports/monitoring_report.md — the same four runs, now queryable.

Cases:
  --case normal      Listing priority query
  --case blocked     Input guardrail fires — logged as guardrail_blocked=True
  --case hitl        iBuyer recommendation — logged as hitl_decision=pending
  --case multi-tool  Cross-segment comparison — multiple tools logged
  --case all         Run all four cases in sequence, then show report (default)
"""

import json
import pathlib
import time
import uuid
from datetime import datetime, timezone

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt.tool_node import ToolCallRequest

from realthor.config import load_config, resolve_paths
from realthor.monitor import RunRecord, compute_metrics, generate_report, load_run_records
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
    },
    "blocked": {
        "query": "What are the executive compensation packages for regional managers?",
    },
    "hitl": {
        "query": (
            "Recommend an iBuyer channel strategy for OPP-00015. "
            "It's a large west house. Submit the recommendation."
        ),
    },
    "multi-tool": {
        "query": (
            "Compare listing priority for west/apartment/2 and north/apartment/2. "
            "Which region has stronger demand?"
        ),
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


def _log_run(cfg: dict, record: RunRecord) -> None:
    log_dir = pathlib.Path(cfg["logging"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "runs.jsonl", "a") as f:
        f.write(json.dumps(record.__dict__) + "\n")


def _run_case(agent, case: str, query: str, cfg: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"{'=' * 60}\n")

    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    model_name = cfg["model"]["name"]
    cost_in = cfg["logging"]["cost_per_1k_tokens_input"]
    cost_out = cfg["logging"]["cost_per_1k_tokens_output"]

    blocked_term = _check_input(query)
    if blocked_term:
        print(f"[GUARDRAIL] Input blocked: '{blocked_term}'")
        print("Agent: This topic is outside the scope of RealThor's capabilities.\n")
        record = RunRecord(
            run_id=run_id, timestamp=timestamp, user_id="demo",
            command="chat", input_text=query, success=True,
            failure_reason="", latency_s=0.05, input_tokens=0,
            output_tokens=0, cost_usd=0.0, tools_called=[],
            guardrail_blocked=True, guardrail_reason=blocked_term,
            hitl_decision="none",
        )
        _log_run(cfg, record)
        return

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    callback = UsageMetadataCallbackHandler()
    t0 = time.perf_counter()
    result = None
    success = True
    failure_reason = ""
    hitl_decision = "none"

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(query)]},
            config={**config, "callbacks": [callback]},
        )

        if result.get("__interrupt__"):
            pending = result["__interrupt__"][0].value
            action = pending["action_requests"][0]
            print(f"[INTERRUPT] Pending approval: {action['name']}")
            print(f"[INTERRUPT] {action['description']}\n")
            print("Action requires approval. Stopping here for the demo.\n")
            hitl_decision = "pending"
        else:
            print(f"Agent:\n{result['messages'][-1].content}\n")
    except Exception as e:
        success = False
        failure_reason = str(e)
        print(f"Error: {failure_reason}\n")

    latency_s = time.perf_counter() - t0
    usage = callback.usage_metadata.get(model_name, {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cost_usd = (input_tokens / 1000) * cost_in + (output_tokens / 1000) * cost_out

    tools_called = []
    if result and isinstance(result, dict):
        for msg in result.get("messages", []):
            if isinstance(msg, ToolMessage) and msg.name:
                tools_called.append(msg.name)

    record = RunRecord(
        run_id=run_id, timestamp=timestamp, user_id="demo",
        command="chat", input_text=query, success=success,
        failure_reason=failure_reason, latency_s=round(latency_s, 3),
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost_usd, tools_called=tools_called,
        guardrail_blocked=False, guardrail_reason="",
        hitl_decision=hitl_decision,
    )
    _log_run(cfg, record)


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
        _run_case(agent, c, info["query"], cfg)

    if case == "all":
        print("\n" + "─" * 60)
        print("Generating monitoring report from logs/runs.jsonl...")
        log_path = pathlib.Path(cfg["logging"]["log_dir"]) / "runs.jsonl"
        output_dir = pathlib.Path(cfg["logging"]["reports_dir"])
        records = load_run_records(log_path)
        metrics = compute_metrics(records)
        generate_report(metrics, output_dir)
        report_path = output_dir / "monitoring_report.md"
        print(f"\nReport written to {report_path}\n")
        print(report_path.read_text())


if __name__ == "__main__":
    main()
