import pathlib

import pandas as pd
import yaml


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_prompt(path: str) -> str:
    with open(path) as f:
        return f.read()


def resolve_paths(cfg: dict, config_path: str) -> dict:
    """Resolve data/prompt paths relative to the config file, not CWD."""
    base = pathlib.Path(config_path).resolve().parent
    cfg["paths"] = {k: str(base / v) for k, v in cfg["paths"].items()}
    return cfg


def build_context(
    demand: pd.DataFrame,
    supply: pd.DataFrame,
    region: str,
    property_type: str,
    bedrooms: int,
) -> str:
    d = demand[
        (demand["region"] == region)
        & (demand["property_type"] == property_type)
        & (demand["bedrooms"] == bedrooms)
    ]
    s = supply[
        (supply["region"] == region)
        & (supply["property_type"] == property_type)
        & (supply["bedrooms"] == bedrooms)
    ]
    if d.empty or s.empty:
        return "No data available for the requested segment."
    return (
        f"Region: {region}\n"
        f"Property: {bedrooms}-bedroom {property_type}\n\n"
        f"Demand signals:\n{d.to_string(index=False)}\n\n"
        f"Supply snapshot:\n{s.to_string(index=False)}"
    )
