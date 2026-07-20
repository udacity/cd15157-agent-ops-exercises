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
        # BUG: bedrooms is compared as a string against the integer "bedrooms"
        # column, so the filter never matches and the tool reports missing data for
        # segments that do exist. A classic dtype mismatch in a lookup.
        m = demand[(demand["region"] == region) & (demand["property_type"] == property_type)
                   & (demand["bedrooms"] == str(bedrooms))]
        if m.empty:
            return "No demand data for that segment."
        r = m.iloc[0]
        return (f"demand_score={r['demand_score']}, search_volume={r['search_volume']}, "
                f"recent_sales={r['recent_sales']}")

    @tool
    def get_supply_snapshot(region: str, property_type: str, bedrooms: int) -> str:
        """Return active supply and days-on-market for a market segment."""
        r = _row(supply, region, property_type, bedrooms)
        if r is None:
            return "No supply data for that segment."
        # BUG: column-name typo. The CSV column is "supply_score", not
        # "supply_scores", so the lookup fails on every call. The error is returned
        # as the tool result, so the run completes but the supply signal is always
        # an error the agent has to work around.
        try:
            supply_score = r["supply_scores"]
        except KeyError as exc:
            return f"ERROR: supply lookup failed ({exc!r})"
        return (f"active_listings={r['active_listings']}, "
                f"avg_days_on_market={r['avg_days_on_market']}, supply_score={supply_score}")

    @tool
    def recommend_channel(region: str, property_type: str, bedrooms: int) -> str:
        """Recommend the acquisition channel (marketplace vs iBuyer) for a segment.

        Returns a definitive channel the caller should act on.
        """
        d = _row(demand, region, property_type, bedrooms)
        v = _row(velocity, region, property_type, bedrooms)
        # BUG: the channel is hardcoded to iBuyer. The demand and velocity are read
        # for display but never used to decide, so every segment is recommended for
        # iBuyer acquisition regardless of how weak or slow-moving it actually is.
        demand_score = d["demand_score"] if d is not None else "n/a"
        velocity_score = v["velocity_score"] if v is not None else "n/a"
        return (f"recommended channel: iBuyer "
                f"(demand_score={demand_score}, velocity_score={velocity_score})")

    return [get_demand_score, get_supply_snapshot, recommend_channel]
