import pandas as pd
from langchain_core.tools import tool


def make_tools(demand: pd.DataFrame, supply: pd.DataFrame) -> list:
    """Build the demo tools, closing over the loaded DataFrames."""

    @tool
    def get_demand_signals(region: str, property_type: str, bedrooms: int) -> str:
        """Get demand signals for a Ciudaty region and property profile."""
        d = demand[
            (demand["region"] == region)
            & (demand["property_type"] == property_type)
            & (demand["bedrooms"] == bedrooms)
        ]
        if d.empty:
            return "No demand data available for this segment."
        return d.to_string(index=False)

    @tool
    def get_supply_snapshot(region: str, property_type: str, bedrooms: int) -> str:
        """Get supply snapshot for a Ciudaty region and property profile."""
        s = supply[
            (supply["region"] == region)
            & (supply["property_type"] == property_type)
            & (supply["bedrooms"] == bedrooms)
        ]
        if s.empty:
            return "No supply data available for this segment."
        return s.to_string(index=False)

    @tool
    def flag_segment_for_review(region: str, property_type: str, bedrooms: int) -> str:
        """Flag a Ciudaty segment for internal priority review. Analyst access required."""
        return f"Segment {region}/{property_type}/{bedrooms}bd flagged for review."

    return [get_demand_signals, get_supply_snapshot, flag_segment_for_review]
