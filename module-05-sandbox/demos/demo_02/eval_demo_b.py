"""Eval runner for demo_01_B cases.

For each case in eval_cases.json:
  1. Runs reference_code in demos/data/ to verify the ground truth answer.
  2. Runs the query through the agent.
  3. Checks whether expected_result appears in the agent's response (substring match).

Exit code 0 if all cases pass, 1 otherwise.
"""
import json
import pathlib
import subprocess
import sys

import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HostExecutionPolicy, ShellToolMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from realthor.config import load_config, make_chat_model, resolve_paths
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")
EVAL_CASES_PATH = pathlib.Path(__file__).parent / "eval_cases.json"


def _build_agent(cfg: dict):
    model = make_chat_model(cfg)

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
        """Use for analytical queries that require filtering or aggregating raw listing data."""
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


def _run_reference(code: str, data_dir: pathlib.Path) -> str:
    """Execute reference_code in data_dir and return stdout."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=data_dir,
    )
    return result.stdout.strip()


def main() -> None:
    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    data_dir = pathlib.Path(cfg["paths"]["demand_data"]).parent

    with open(EVAL_CASES_PATH) as f:
        cases = json.load(f)

    print("Loading agent...")
    agent = _build_agent(cfg)
    print()

    failures = []
    for row in cases:
        case = row["case"]
        query = row["query"]
        expected = row["expected_result"]
        ref_code = row["reference_code"]

        # Step 1: verify reference code produces the expected result
        ref_output = _run_reference(ref_code, data_dir)
        ref_ok = expected in ref_output

        # Step 2: run agent
        result = agent.invoke({"messages": [HumanMessage(query)]})
        agent_answer = result["messages"][-1].content
        agent_ok = expected.lower() in agent_answer.lower()

        status = "PASS" if (ref_ok and agent_ok) else "FAIL"
        if status == "FAIL":
            failures.append(case)

        ref_label = ref_output[:30].replace("\n", " ")
        agent_label = agent_answer[:60].replace("\n", " ")
        print(f"  {case:<14} reference={ref_label:<14} agent={agent_label[:40]}  [{status}]")
        if not ref_ok:
            print(f"    ✗ reference code output '{ref_output}' does not contain '{expected}'")
        if not agent_ok:
            print(f"    ✗ agent answer does not contain '{expected}'")

    print()
    total = len(cases)
    passed = total - len(failures)
    print(f"{passed}/{total} cases passed")
    if failures:
        print(f"Failed: {failures}")
        sys.exit(1)
    print("All cases passed.")


if __name__ == "__main__":
    main()
