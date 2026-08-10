from pathlib import Path

import pandas as pd
from fastmcp import FastMCP

DEMAND = pd.read_csv(Path(__file__).parent / "data" / "demand.csv")

mcp = FastMCP("ciudaty-data")


@mcp.tool
def get_demand_score(region: str, property_type: str, bedrooms: int) -> str:
    """Return the demand score for a Ciudaty market segment."""
    row = DEMAND[
        (DEMAND["region"] == region)
        & (DEMAND["property_type"] == property_type)
        & (DEMAND["bedrooms"] == bedrooms)
    ]
    if row.empty:
        return "No demand data for this segment."
    r = row.iloc[0]
    return f"Demand score for {bedrooms}-bed {property_type} in {region}: {r['demand_score']} (search volume {r['search_volume']})."


@mcp.tool
def list_segments() -> str:
    """List the market segments this server has data for."""
    return DEMAND[["region", "property_type", "bedrooms"]].to_string(index=False)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=False)
