"""Policy evaluation for RealThor channel recommendations.

Policies evaluate conditions and return decisions — they are conditional.
Guardrails enforce constraints unconditionally.
"""

from dataclasses import dataclass


@dataclass
class PolicyDecision:
    requires_approval: bool
    reason: str = ""
    risk_level: str = "low"  # "low" | "medium" | "high"


def evaluate_channel_policy(
    channel: str,
    estimated_value: float,
    role: str,
    threshold: float,
) -> PolicyDecision:
    """Evaluate whether a channel recommendation requires human approval.

    Args:
        channel: Recommended channel ("marketplace" or "ibuyer").
        estimated_value: Estimated investment value for the opportunity.
        role: Caller's role (passed to support future per-role thresholds).
        threshold: Investment amount above which iBuyer requires approval.

    Returns:
        PolicyDecision with requires_approval, reason, and risk_level.
    """
    # TODO: Implement this function.
    #
    # Rules:
    #   - marketplace → requires_approval=False, risk_level="low"
    #   - ibuyer + estimated_value > threshold → requires_approval=True,
    #       risk_level="high", reason includes both dollar amounts
    #   - ibuyer + estimated_value <= threshold → requires_approval=False,
    #       risk_level="medium"
    #   - unknown channel → requires_approval=False, risk_level="low"
    #
    # Hint: use f-strings to format dollar amounts as ${value:,.0f}
    #       so "$610,000" not "610000.0"
    raise NotImplementedError("Implement evaluate_channel_policy")
