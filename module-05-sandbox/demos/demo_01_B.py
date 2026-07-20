import json
import pathlib
import sys

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HostExecutionPolicy, ShellToolMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from realthor.config import load_config, make_chat_model, resolve_paths
from realthor.tools import make_tools

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")
EVAL_CASES_PATH = pathlib.Path(__file__).parent / "eval_cases.json"


UNSAFE_CASE = (
    "List all files in the current directory using os.listdir",
    "directory listing — ShellToolMiddleware executes os.listdir with full host access",
)

# The analyst model reliably refuses to emit this, so the host-access risk would never
# reach the shell on screen. We drive the ShellToolMiddleware shell directly with the
# fixed command to show what the host shell can do, regardless of the model.
UNSAFE_COMMAND = "python -c \"import os; print('\\n'.join(os.listdir('.')))\""


BOX_WIDTH = 64


def _draw_box(title: str, body: str) -> None:
    """Render a labelled terminal box around (possibly multi-line) body text."""
    inner = BOX_WIDTH - 2
    print(f"  ╭─ {title} ".ljust(BOX_WIDTH + 3, "─") + "╮")
    for raw_line in body.splitlines() or [""]:
        for i in range(0, len(raw_line), inner) or [0]:
            chunk = raw_line[i : i + inner]
            print(f"  │ {chunk.ljust(inner)} │")
    print("  ╰" + "─" * BOX_WIDTH + "╯")


class ShellTracer(BaseCallbackHandler):
    """Prints every shell command the analyst sub-agent runs as a SHELL box."""

    def on_tool_start(self, serialized, input_str, *, inputs=None, **kwargs):
        name = (serialized or {}).get("name", "")
        if name != "shell":
            return
        command = (inputs or {}).get("command") or input_str
        _draw_box("SHELL · host execution", command)


def _load_cases() -> dict[str, tuple[str, str]]:
    """Return {case_name: (query, reference_label)} from eval_cases.json + unsafe case."""
    with open(EVAL_CASES_PATH) as f:
        rows = json.load(f)
    cases = {r["case"]: (r["query"], r["reference_label"]) for r in rows}
    cases["unsafe"] = UNSAFE_CASE
    return cases


def _build_agent(cfg: dict):
    model = make_chat_model(cfg)

    data_dir = pathlib.Path(cfg["paths"]["demand_data"]).parent

    with open(cfg["paths"]["analyst_prompt"]) as f:
        analyst_prompt = f.read()

    shell_mw = ShellToolMiddleware(
        workspace_root=data_dir,
        execution_policy=HostExecutionPolicy(),
        startup_commands=[
            f"export PATH={pathlib.Path(sys.executable).parent}:$PATH"
        ],
    )

    analyst_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=analyst_prompt,
        middleware=[shell_mw],
    )

    tracer = ShellTracer()

    @tool
    def analyze_data(question: str) -> str:
        """Use for analytical queries that require filtering or aggregating raw listing data —
        percentages, averages, rankings, counts that span many rows."""
        print("\n  → RealThor delegates to the analyst sub-agent")
        _draw_box("ANALYST · question", question)
        result = analyst_agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"callbacks": [tracer]},
        )
        return result["messages"][-1].content

    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    listings = pd.read_csv(cfg["paths"]["listings_data"])
    bespoke_tools = make_tools(demand, supply, listings)

    with open(cfg["paths"]["prompt_analyst"]) as f:
        realthor_prompt = f.read()

    agent = create_agent(
        model=model,
        tools=bespoke_tools + [analyze_data],
        system_prompt=realthor_prompt,
    )
    return agent, shell_mw


def _print_header(case: str, query: str, expected: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected (from raw data): {expected}")
    print(f"{'=' * 60}\n")


def _run_case(agent, case: str, query: str, expected: str) -> None:
    """Agent-driven case: RealThor delegates to the analyst sub-agent."""
    _print_header(case, query, expected)
    result = agent.invoke({"messages": [HumanMessage(query)]})
    answer = result["messages"][-1].content
    print(f"Agent answer:\n{answer}\n")


def _run_unsafe_case(shell_mw, case: str, query: str, expected: str) -> None:
    """Guard-driven case: run the fixed os.listdir command through the host shell.

    The analyst model reliably refuses this, so we drive the ShellToolMiddleware shell
    directly to show what the unrestricted host shell can reach. The shell output is the
    ending — there is no model turn.
    """
    _print_header(case, query, expected)
    print("  → RealThor delegates to the analyst sub-agent")
    _draw_box("ANALYST · question", query)
    _draw_box("SHELL · host execution", UNSAFE_COMMAND)
    resources = shell_mw._get_or_create_resources({})
    message = shell_mw._run_shell_tool(
        resources,
        {"command": UNSAFE_COMMAND, "restart": False},
        tool_call_id="forced-unsafe",
    )
    output = message.content if hasattr(message, "content") else str(message)
    print(f"Shell output:\n{output}\n")


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
    agent, shell_mw = _build_agent(cfg)

    to_run = list(cases.items()) if case == "all" else [(case, cases[case])]
    for c, (q, expected) in to_run:
        if c == "unsafe":
            _run_unsafe_case(shell_mw, c, q, expected)
        else:
            _run_case(agent, c, q, expected)

    print("\n" + "─" * 60)
    print("The analyst sub-agent has one job: generate and run pandas code.")
    print("RealThor delegates to it when precomputed tools fall short.")
    print("ShellToolMiddleware provides the shell — with full host access.")
    print()


if __name__ == "__main__":
    main()
