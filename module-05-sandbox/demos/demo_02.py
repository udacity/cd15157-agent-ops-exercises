import pathlib
import sys

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from realthor.config import load_config, make_chat_model, resolve_paths
from realthor.sandbox import run_sandboxed, validate_code

load_dotenv()

CONFIG_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

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
        "Run an unbounded loop that never terminates",
        "BLOCKED — execution timed out (sandbox enforces 30-second limit)",
    ),
}

# The blocked and timeout cases are driven straight into execute_python instead of
# through the model, which reliably refuses to emit this code. The AST/runtime guard
# is what we want on screen, so we hand it the adversarial code directly.
FORCED_CODE = {
    "blocked": "import os\nprint(os.listdir('.'))",
    "timeout": "total = 0\nwhile True:\n    total = total + 1\nprint(total)",
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
        _draw_box("SANDBOX · execute_python", code)
        ok, reason = validate_code(code)
        if not ok:
            print(f"  ✗ blocked: {reason}\n")
            return f"BLOCKED: {reason}"
        output, error = run_sandboxed(code, dataframes, timeout=timeout)
        if error:
            print(f"  ✗ blocked: {error}\n")
            return f"BLOCKED: {error}"
        print("  ✓ validated · ran in sandbox\n")
        return output or "(no output)"

    return execute_python


def _build_agent(cfg: dict, execute_python):
    model = make_chat_model(cfg)
    with open(cfg["paths"]["prompt_sandbox"]) as f:
        system_prompt = f.read()

    return create_agent(model=model, tools=[execute_python], system_prompt=system_prompt)


def _print_header(case: str, query: str, label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Case: {case}")
    print(f"Query: {query}")
    print(f"Expected: {label}")
    print(f"{'=' * 60}\n")


def _run_case(agent, case: str, query: str, label: str) -> None:
    """Agent-driven case: RealThor writes and runs the pandas code itself."""
    _print_header(case, query, label)
    result = agent.invoke({"messages": [HumanMessage(query)]})
    answer = result["messages"][-1].content
    print(f"Agent answer:\n{answer}\n")


def _run_forced_case(execute_python, case: str, query: str, label: str, code: str) -> None:
    """Guard-driven case: hand adversarial code straight to execute_python.

    The model reliably refuses to emit this code, so the AST/runtime guard would never
    fire on screen. Driving the tool directly makes the block deterministic. The tool's
    returned string is the ending — there is no model turn.
    """
    _print_header(case, query, label)
    returned = execute_python.invoke({"code": code})
    print(f"Tool returned: {returned}\n")


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
    execute_python = _build_execute_python_tool(cfg)
    agent = _build_agent(cfg, execute_python)

    cases_to_run = list(CASES.items()) if case == "all" else [(case, CASES[case])]
    for c, (q, label) in cases_to_run:
        if c in FORCED_CODE:
            _run_forced_case(execute_python, c, q, label, FORCED_CODE[c])
        else:
            _run_case(agent, c, q, label)

    print("\n" + "─" * 60)
    print("The sandbox runs the same pandas code — but blocks dangerous imports.")
    print("AST validation fires before execution. No shell access. No network.")
    print()


if __name__ == "__main__":
    main()
