from __future__ import annotations

import click
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from realthor.config import load_config, load_prompt, resolve_paths
from realthor.guardrails import GUEST_CONTEXT, RealThorGuardrails, UserContext
from realthor.tools import make_tools

load_dotenv()


def _resolve_user(user_id: str, users_path: str) -> UserContext:
    """TODO B: Look up user_id in users.csv and return a UserContext.

    If user_id is empty or not found in users.csv, return GUEST_CONTEXT.

    Steps:
      1. If not user_id: return GUEST_CONTEXT
      2. Read users_path with pd.read_csv()
      3. Filter rows where users["user_id"] == user_id
      4. If no match: return GUEST_CONTEXT
      5. Take the first matching row and return:
           UserContext(
               user_id=str(row["user_id"]),
               role=str(row["role"]),
               region_access=str(row["region_access"]),
           )
    """
    raise NotImplementedError


def build_agent(config_path: str = "config.yaml"):
    cfg = resolve_paths(load_config(config_path), config_path)
    model = ChatOpenAI(
        model=cfg["model"]["name"],
        temperature=cfg["model"]["temperature"],
    )
    system_prompt = load_prompt(cfg["paths"]["prompt"])
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    neighborhoods = pd.read_csv(cfg["paths"]["neighborhood_data"])
    velocity = pd.read_csv(cfg["paths"]["velocity_data"])
    supply_opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])
    listing_data = pd.read_csv(cfg["paths"]["listings_data"])
    sales_data = pd.read_csv(cfg["paths"]["sales_data"])
    tools = make_tools(demand, supply, neighborhoods, velocity, supply_opps, listing_data, sales_data)
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        # TODO C: Add context_schema=UserContext
        # TODO C: Add middleware=[RealThorGuardrails()]
    )


@click.group()
def app():
    """RealThor — Listing Supply Intelligence CLI."""


@app.command()
@click.option("--region", required=True, help="Ciudaty region (west, north, south, east, center)")
@click.option("--property-type", "property_type", required=True, help="apartment, house, or studio")
@click.option("--bedrooms", required=True, type=int, help="Number of bedrooms")
# TODO A: Add --user option: @click.option("--user", "user_id", default="", help="User ID from users.csv")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
def analyze(region, property_type, bedrooms, config_path):
    """Analyze listing priority for one region/property profile."""
    click.echo("Loading agent...")
    cfg = resolve_paths(load_config(config_path), config_path)

    # TODO A+B: Replace the line below with _resolve_user(user_id, cfg["paths"]["users_data"])
    user_ctx = GUEST_CONTEXT

    click.echo(f"Identity: {user_ctx.user_id or 'guest'} ({user_ctx.role})")
    agent = build_agent(config_path)
    question = (
        f"What's the listing priority for {bedrooms}-bedroom "
        f"{property_type} in the {region} region?"
    )
    click.echo("Analyzing...")
    result = agent.invoke(
        {"messages": [HumanMessage(question)]},
        # TODO D: Add context=user_ctx
    )
    click.echo(result["messages"][-1].content)


@app.command()
@click.option("--user", "-u", "user_id", default="", help="User ID resolved from users.csv")
@click.option("--message", "-m", required=True, help="Free-text message to send to the agent")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
def chat(user_id, message, config_path):
    """Send a free-text message to the agent (all three guardrail layers active)."""
    click.echo("Loading agent...")
    cfg = resolve_paths(load_config(config_path), config_path)
    user_ctx = _resolve_user(user_id, cfg["paths"]["users_data"])
    click.echo(f"Identity: {user_ctx.user_id or 'guest'} ({user_ctx.role})")
    agent = build_agent(config_path)
    click.echo("Analyzing...")
    result = agent.invoke(
        {"messages": [HumanMessage(message)]},
        context=user_ctx,
    )
    click.echo(result["messages"][-1].content)
