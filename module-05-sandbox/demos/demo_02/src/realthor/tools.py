import pandas as pd
from langchain_core.tools import tool


def make_tools(
    demand: pd.DataFrame,
    supply: pd.DataFrame,
    listings: pd.DataFrame,
) -> list:
    """Build the three bespoke demo tools, closing over the loaded DataFrames.

    All three tools require a complete segment (region + property_type + bedrooms)
    and return precomputed or derived scores. They cannot answer row-level filtering
    or cross-segment aggregation queries — that is the static tool ceiling this demo shows.
    """

    @tool
    def get_demand_signals(region: str, property_type: str, bedrooms: int) -> str:
        """Get demand signals for a Ciudaty segment.

        Returns demand score, lead count, and recent sales volume.

        Args:
            region: Ciudaty region (west, north, south, east, center)
            property_type: Property type (apartment, house, studio)
            bedrooms: Number of bedrooms
        """
        d = demand[
            (demand["region"] == region)
            & (demand["property_type"] == property_type)
            & (demand["bedrooms"] == bedrooms)
        ]
        if d.empty:
            return f"No demand data for {region}/{property_type}/{bedrooms}br."

        row = d.iloc[0]
        return (
            f"Segment: {region}/{property_type}/{bedrooms}br\n"
            f"Demand score: {float(row['demand_score'])}\n"
            f"Lead count: {int(row['lead_count'])}\n"
            f"Recent sales: {int(row['recent_sales'])}"
        )

    @tool
    def get_supply_snapshot(region: str, property_type: str, bedrooms: int) -> str:
        """Get a supply snapshot for a Ciudaty segment.

        Returns active listing count, average days on market, and supply score.

        Args:
            region: Ciudaty region (west, north, south, east, center)
            property_type: Property type (apartment, house, studio)
            bedrooms: Number of bedrooms
        """
        s = supply[
            (supply["region"] == region)
            & (supply["property_type"] == property_type)
            & (supply["bedrooms"] == bedrooms)
        ]
        if s.empty:
            return f"No supply data for {region}/{property_type}/{bedrooms}br."

        row = s.iloc[0]
        return (
            f"Segment: {region}/{property_type}/{bedrooms}br\n"
            f"Active listings: {int(row['active_listings'])}\n"
            f"Avg days on market: {float(row['avg_days_on_market']):.1f}\n"
            f"Supply score: {float(row['supply_score'])}"
        )

    @tool
    def get_listing_priority(region: str, property_type: str, bedrooms: int) -> str:
        """Get the listing priority assessment for a Ciudaty segment.

        Returns priority level, recommended action, demand score, supply score,
        and active listing count.

        Args:
            region: Ciudaty region (west, north, south, east, center)
            property_type: Property type (apartment, house, studio)
            bedrooms: Number of bedrooms
        """
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
            return f"No data for {region}/{property_type}/{bedrooms}br."

        ds = float(d.iloc[0]["demand_score"])
        ss = float(s.iloc[0]["supply_score"])
        active = int(s.iloc[0]["active_listings"])

        if ds >= 0.75 and ss <= 0.35:
            priority, action = "high", "prioritize_new_listings"
        elif ds >= 0.55 or ss <= 0.55:
            priority, action = "medium", "monitor_closely"
        else:
            priority, action = "low", "deprioritize"

        return (
            f"Segment: {region}/{property_type}/{bedrooms}br\n"
            f"Priority: {priority}\n"
            f"Action: {action}\n"
            f"Demand score: {ds}\n"
            f"Supply score: {ss}\n"
            f"Active listings: {active}"
        )

    return [get_demand_signals, get_supply_snapshot, get_listing_priority]
