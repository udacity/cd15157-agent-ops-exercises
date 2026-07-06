import click
import pandas as pd

from realthor.config import build_context, load_config, resolve_paths


@click.group()
def app():
    """RealThor — Listing Supply Intelligence CLI."""


@app.command()
@click.option("--region", required=True, help="Ciudaty region (west, north, south, east, center)")
@click.option("--property-type", "property_type", required=True, help="apartment, house, or studio")
@click.option("--bedrooms", required=True, type=int, help="Number of bedrooms")
@click.option("--config", "config_path", default="config.yaml", show_default=True, help="Path to config file")
def lookup(region, property_type, bedrooms, config_path):
    """Look up demand and supply signals for a segment."""
    cfg = resolve_paths(load_config(config_path), config_path)
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    context = build_context(demand, supply, region, property_type, bedrooms)
    click.echo(context)
