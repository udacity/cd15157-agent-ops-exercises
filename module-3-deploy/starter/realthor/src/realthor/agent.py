"""
RealThor agent — Module 3 exercise skeleton.

Implement build_agent() and the analyze command so that:
    uv run realthor analyze --region west --property-type apartment --bedrooms 2
calls the agent and prints a recommendation.
"""

from dotenv import load_dotenv
import click
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from realthor.config import load_config, load_prompt, resolve_paths
from realthor.tools import make_tools

load_dotenv()


def build_agent(config_path: str = "config.yaml"):
    cfg = resolve_paths(load_config(config_path), config_path)
    # TODO: create a ChatOpenAI model using cfg["model"]["name"] and cfg["model"]["temperature"]
    # TODO: load the system prompt with load_prompt(cfg["paths"]["prompt"])
    # TODO: load demand and supply DataFrames with pd.read_csv()
    # TODO: call make_tools(demand, supply) to get the tool list
    # TODO: return create_agent(model=..., tools=..., system_prompt=...)
    pass


@click.group()
def app():
    """RealThor — Listing Supply Intelligence CLI."""


@app.command()
@click.option("--region", required=True, help="Ciudaty region (west, north, south, east, center)")
@click.option("--property-type", "property_type", required=True, help="apartment, house, or studio")
@click.option("--bedrooms", required=True, type=int, help="Number of bedrooms")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
def analyze(region, property_type, bedrooms, config_path):
    """Analyze listing priority for one region/property profile."""
    click.echo("Loading agent...")
    # TODO: call build_agent(config_path) to get the agent
    # TODO: build a question string using region, property_type, bedrooms
    click.echo("Analyzing...")
    # TODO: call agent.invoke({"messages": [HumanMessage(question)]})
    # TODO: print result["messages"][-1].content
    pass
