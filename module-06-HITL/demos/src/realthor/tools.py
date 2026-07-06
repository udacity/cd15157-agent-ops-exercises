"""Demo tools for M06 HITL module.

Simplified to only the tools needed for the demo:
- get_supply_opportunities: look up opportunities by segment
- submit_channel_recommendation: submit a channel recommendation (pure action)
"""

import json
import pathlib

import pandas as pd
from langchain_core.tools import tool


def make_tools(cfg: dict) -> list:
    """Build the two demo tools, closing over loaded data."""
    opps = pd.read_csv(cfg["paths"]["supply_opportunities_data"])
    rec_path = pathlib.Path(cfg["paths"]["channel_recommendations"])
    rec_path.parent.mkdir(parents=True, exist_ok=True)

    @tool
    def get_supply_opportunities(region: str, property_type: str, bedrooms: int) -> str:
        """Get supply opportunities for a Ciudaty segment.

        Returns a list of opportunities with ID, type (ibuyer/marketplace),
        estimated value, and pipeline stage.

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

        Marketplace recommendations are submitted automatically.
        iBuyer recommendations above the approval threshold require operator review.

        Args:
            opportunity_id: Supply opportunity ID (e.g., OPP-00015)
            channel: Recommended channel ("marketplace" or "ibuyer")
            notes: Analyst notes on the recommendation
        """
        row = opps[opps["supply_opportunity_id"] == opportunity_id]
        if row.empty:
            return json.dumps({"status": "error", "message": f"Opportunity {opportunity_id} not found"})

        record = {
            "opportunity_id": opportunity_id,
            "channel": channel,
            "estimated_value": float(row.iloc[0]["estimated_value"]),
            "notes": notes,
        }
        with open(rec_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        return json.dumps({
            "status": "success",
            "opportunity_id": opportunity_id,
            "channel": channel,
            "message": f"Channel recommendation ({channel}) submitted for {opportunity_id}.",
        })

    return [get_supply_opportunities, submit_channel_recommendation]
