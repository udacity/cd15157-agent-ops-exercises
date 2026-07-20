import json
import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain.agents.middleware._redaction import PIIDetectionError
from langchain_core.messages import HumanMessage

from realthor.config import load_config, load_prompt, make_chat_model, resolve_paths
from realthor.tools import make_tools

load_dotenv()

QUERY = "My email is broker@ciudaty.com. Show me demand signals for west apartments with 2 bedrooms."


def _build(middleware=None):
    cfg = resolve_paths(load_config("config.yaml"), "config.yaml")
    model = make_chat_model(cfg)
    system_prompt = load_prompt(cfg["paths"]["prompt"])
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    tools = make_tools(demand, supply)
    kw = {"middleware": [middleware]} if middleware else {}
    return create_agent(model=model, tools=tools, system_prompt=system_prompt, **kw)


def case_no_guardrail():
    print("\n--- PII in input (no guardrail) ---")
    print(f"Input:  {QUERY}")
    agent = _build()
    r = agent.invoke({"messages": [HumanMessage(QUERY)]})
    print(f"Output:\n{r['messages'][-1].content}")


def case_pii_middleware():
    print("\n--- PII in input (PIIMiddleware blocks it) ---")
    print(f"Input:  {QUERY}")
    agent = _build(PIIMiddleware("email", strategy="block"))
    try:
        r = agent.invoke({"messages": [HumanMessage(QUERY)]})
        print(f"Output:\n{r['messages'][-1].content}")
    except PIIDetectionError as e:
        print(f"Output:\n{json.dumps({'status': 'blocked', 'reason': 'pii_detected', 'message': str(e)})}")


CASES = {
    "no-guardrail": case_no_guardrail,
    "pii-middleware": case_pii_middleware,
}


@click.command()
@click.option("--case", default="all", type=click.Choice([*CASES, "all"]), show_default=True)
def main(case):
    if case == "all":
        for fn in CASES.values():
            fn()
    else:
        CASES[case]()


if __name__ == "__main__":
    main()
