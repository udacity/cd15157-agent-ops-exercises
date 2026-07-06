"""A reduced RealThor toolset for the debugging demo.

Three tools over the aggregate demand/supply/velocity signals — enough to produce
a real tool trajectory for the North iBuyer question without the full 15-tool
solution stack.
"""

import pandas as pd
from langchain_core.tools import tool


def make_tools(cfg: dict) -> list:
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    velocity = pd.read_csv(cfg["paths"]["velocity_data"])

    def _row(df, region, property_type, bedrooms):
        m = df[(df["region"] == region) & (df["property_type"] == property_type)
               & (df["bedrooms"] == int(bedrooms))]
        return None if m.empty else m.iloc[0]

    @tool
    def get_demand_score(region: str, property_type: str, bedrooms: int) -> str:
        """Return the demand score and signals for a market segment."""
        r = _row(demand, region, property_type, bedrooms)
        if r is None:
            return "No demand data for that segment."
        return (f"demand_score={r['demand_score']}, search_volume={r['search_volume']}, "
                f"recent_sales={r['recent_sales']}")

    @tool
    def get_supply_snapshot(region: str, property_type: str, bedrooms: int) -> str:
        """Return active supply and days-on-market for a market segment."""
        r = _row(supply, region, property_type, bedrooms)
        if r is None:
            return "No supply data for that segment."
        return (f"active_listings={r['active_listings']}, "
                f"avg_days_on_market={r['avg_days_on_market']}, supply_score={r['supply_score']}")

    @tool
    def recommend_channel(region: str, property_type: str, bedrooms: int) -> str:
        """Recommend marketplace vs iBuyer for a segment, using demand and velocity."""
        d = _row(demand, region, property_type, bedrooms)
        v = _row(velocity, region, property_type, bedrooms)
        if d is None or v is None:
            return "Insufficient data to recommend a channel."
        return (f"inputs: demand_score={d['demand_score']}, velocity_score={v['velocity_score']}; "
                f"decide marketplace vs iBuyer from these.")

    return [get_demand_score, get_supply_snapshot, recommend_channel]
