"""Demo tools for M07 monitoring module.

Simplified to tools needed for the four demo cases:
- get_listing_priority: signal for normal/multi-tool cases
- get_supply_opportunities: look up opportunities
- submit_channel_recommendation: channel action (HITL case)
"""

import json
import pathlib

import pandas as pd
from langchain_core.tools import tool


def make_tools(cfg: dict) -> list:
    """Build demo tools, closing over loaded data."""
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    velocity = pd.read_csv(cfg["paths"]["velocity_data"])
    opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])
    rec_path = pathlib.Path(cfg["paths"]["channel_recommendations"])
    rec_path.parent.mkdir(parents=True, exist_ok=True)

    @tool
    def get_listing_priority(region: str, property_type: str, bedrooms: int) -> str:
        """Get listing priority for a Ciudaty segment.

        Returns demand score, supply score, velocity score, and recommended action.

        Args:
            region: Ciudaty region (west, north, south, east, center)
            property_type: Property type (apartment, house, studio)
            bedrooms: Number of bedrooms
        """
        d_row = demand[
            (demand["region"] == region)
            & (demand["property_type"] == property_type)
            & (demand["bedrooms"] == bedrooms)
        ]
        s_row = supply[
            (supply["region"] == region)
            & (supply["property_type"] == property_type)
            & (supply["bedrooms"] == bedrooms)
        ]
        v_row = velocity[
            (velocity["region"] == region)
            & (velocity["property_type"] == property_type)
            & (velocity["bedrooms"] == bedrooms)
        ]
        if d_row.empty or s_row.empty:
            return f"No data for {region}/{property_type}/{bedrooms}br."
        d = d_row.iloc[0]
        s = s_row.iloc[0]
        v = v_row.iloc[0] if not v_row.empty else None
        active = int(s["active_listings"])
        demand_score = float(d["demand_score"])
        supply_score = float(d["supply_score"])
        velocity_score = float(v["velocity_score"]) if v is not None else None

        if demand_score >= 0.7 and supply_score <= 0.5:
            priority = "high"
            action = "prioritize_new_listings"
        elif demand_score <= 0.3 or supply_score >= 0.8:
            priority = "low"
            action = "deprioritize"
        else:
            priority = "medium"
            action = "monitor_opportunity"

        result = (
            f"Listing priority for {region}/{property_type}/{bedrooms}br: {priority}\n"
            f"  demand_score={demand_score:.2f}, supply_score={supply_score:.2f}, "
            f"active_listings={active}\n"
            f"  Recommended action: {action}"
        )
        if velocity_score is not None:
            result += f"\n  velocity_score={velocity_score:.2f}"
        return result

    @tool
    def get_supply_opportunities(region: str, property_type: str, bedrooms: int) -> str:
        """Get supply opportunities for a Ciudaty segment.

        Returns a list of opportunities with ID, type, estimated value, and stage.

        Args:
            region: Ciudaty region (west, north, south, east, center)
            property_type: Property type (apartment, house, studio)
            bedrooms: Number of bedrooms
        """
        matches = opps[
            (opps["region"] == region)
            & (opps["property_type"] == property_type)
            & (opps["bedrooms"] == bedrooms)
        ]
        if matches.empty:
            return f"No supply opportunities for {region}/{property_type}/{bedrooms}br."

        results = []
        for _, row in matches.iterrows():
            results.append(
                f"- {row['supply_opportunity_id']}: {row['opportunity_type']}, "
                f"${float(row['estimated_value']):,.0f}, stage={row['pipeline_stage']}"
            )
        return f"Supply opportunities for {region}/{property_type}/{bedrooms}br:\n" + "\n".join(results)

    @tool
    def submit_channel_recommendation(
        opportunity_id: str,
        channel: str,
        notes: str,
    ) -> str:
        """Submit a channel recommendation for a supply opportunity.

        Marketplace recommendations execute automatically.
        iBuyer recommendations above the threshold require operator review.

        Args:
            opportunity_id: The supply opportunity ID (e.g. OPP-00015)
            channel: Channel type: 'marketplace' or 'ibuyer'
            notes: Optional notes for the recommendation
        """
        record = {
            "opportunity_id": opportunity_id,
            "channel": channel,
            "notes": notes,
        }
        with open(rec_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        if channel == "ibuyer":
            return f"iBuyer channel recommendation approved and submitted for {opportunity_id}."
        return f"Marketplace channel recommendation submitted for {opportunity_id}."

    return [get_listing_priority, get_supply_opportunities, submit_channel_recommendation]
