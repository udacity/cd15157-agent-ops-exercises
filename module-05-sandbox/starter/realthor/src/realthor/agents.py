import pandas as pd
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from realthor.config import load_prompt
from realthor.guardrails import UserContext, make_guardrails
from realthor.tools import make_execute_python_tool, make_tools


def build_analyst_agent(cfg: dict):
    """Build the analyst sub-agent: execute_python only, no guardrails.

    The analyst agent is a simple create_agent with:
      - model loaded from cfg
      - analyst_prompt loaded from cfg["paths"]["analyst_prompt"]
      - tools: [make_execute_python_tool(cfg)]

    No middleware — the analyst is internal and not user-facing.
    """
    # TODO: create a ChatOpenAI model from cfg
    # TODO: load analyst_prompt from cfg["paths"]["analyst_prompt"]
    # TODO: build tools list with make_execute_python_tool(cfg)
    # TODO: return create_agent(model=model, tools=tools, system_prompt=analyst_prompt)
    raise NotImplementedError


def build_main_agent(cfg: dict):
    """Build the main RealThor agent with bespoke tools + analyst delegation + guardrails.

    1. Build the analyst sub-agent via build_analyst_agent(cfg).
    2. Wrap it as an analyze_data @tool that invokes analyst and returns the last message.
    3. Load all DataFrames from cfg paths and call make_tools(...) for bespoke tools.
    4. Combine bespoke_tools + [analyze_data] and pass to create_agent with guardrails.
    """
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    system_prompt = load_prompt(cfg["paths"]["prompt"])

    # TODO: call build_analyst_agent(cfg) to create the analyst sub-agent
    analyst = None  # replace with build_analyst_agent(cfg)

    @tool
    def analyze_data(question: str) -> str:
        """Delegate analytical queries requiring filtering or aggregation of raw listing data —
        percentages, averages, rankings, counts that span many rows."""
        # TODO: invoke the analyst agent with the question and return the last message content
        raise NotImplementedError

    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    neighborhoods = pd.read_csv(cfg["paths"]["neighborhood_data"])
    velocity = pd.read_csv(cfg["paths"]["velocity_data"])
    supply_opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])
    listing_data = pd.read_csv(cfg["paths"]["listings_data"])
    sales_data = pd.read_csv(cfg["paths"]["sales_data"])
    bespoke_tools = make_tools(demand, supply, neighborhoods, velocity, supply_opps, listing_data, sales_data)

    return create_agent(
        model=model,
        tools=bespoke_tools + [analyze_data],
        system_prompt=system_prompt,
        context_schema=UserContext,
        middleware=make_guardrails(),
    )
