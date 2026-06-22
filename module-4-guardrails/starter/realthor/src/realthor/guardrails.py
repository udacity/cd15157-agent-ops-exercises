from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime


# ---------------------------------------------------------------------------
# Identity context — resolved from users.csv, never from caller claims
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    """Who is making the request. Set once in agent.py before invocation."""
    user_id: str = ""
    role: str = "guest"       # "analyst" | "broker" | "guest"
    region_access: str = ""   # "all" for analysts; "west|south" for brokers; "" for guest

    def can_access_region(self, region: str) -> bool:
        """TODO: Implement region access check.

        Rules:
          - analyst with region_access="all" can access any region
          - broker can access their pipe-separated regions (e.g. "west|south")
          - guest (region_access="") can access nothing

        Return True if this user can query the given region.
        """
        raise NotImplementedError


GUEST_CONTEXT = UserContext()


# ---------------------------------------------------------------------------
# Policy constants — Layer 1 (input)
# ---------------------------------------------------------------------------

DEMOGRAPHIC_TERMS = [
    "income area", "low-income", "high-income", "credit access",
    "ethnicity", "ethnic", "race", "racial", "demographic",
    "gentrification", "underserved neighborhood", "socioeconomic",
    "poverty rate", "wealth distribution", "income distribution",
]

PERSONA_ESCALATION_PHRASES = [
    "pretend you are", "act as an", "act as a ", "you are now",
    "act like an analyst", "ignore your role", "forget your instructions",
    "override your", "bypass your", "as an internal analyst",
    "as if you were an analyst", "with full access",
]

TOPIC_DEVIATION_TERMS = [
    "who won", "who is winning", "who beat", "score of",
    "world cup", "soccer", "football", "nba", "basketball",
    "stock", "weather", "forecast", "python", "recipe",
    "news", "celebrity", "movie", "music", "tips", "review",
]

GEOGRAPHY_TERMS = [
    "new york", "los angeles", "london", "paris", "barcelona",
    "madrid", "berlin", "dubai", "singapore", "sydney",
    "toronto", "chicago", "miami", "boston", "amsterdam",
    "tokyo", "hong kong", "new york city",
]


# ---------------------------------------------------------------------------
# Policy constants — Layer 2 (tool)
# ---------------------------------------------------------------------------

SENSITIVE_FIELDS = [
    "demographic_notes",
    "seller_name", "seller_motivation",
    "owner_contact", "acquisition_strategy", "internal_score",
    "buyer_name", "credit_score_band", "pre_approval_status",
    "commission_amount", "agent_performance_score",
]

ACTION_TOOLS = {"flag_segment_for_review", "create_segment_report"}

MUTATION_TOOLS = {
    "update_listing", "delete_record", "overwrite_dataset", "add_record",
    "update_asking_price", "delete_lead", "overwrite_csv",
}


# ---------------------------------------------------------------------------
# Policy constants — Layer 3 (output)
# ---------------------------------------------------------------------------

SENSITIVE_OUTPUT_PHRASES = [
    "demographic transition",
    "underserved area",
    "underserved neighborhood",
    "minority neighborhood",
    "credit-challenged",
    "low income concentration",
    "seller's motivation",
    "seller motivation is",
    "seller contact",
    "owner contact",
]

PROFANITY_OUTPUT_MARKERS = [
    "incompetent", "terrible brokers", "useless agents", "pathetic",
    "disgusting", "horrible performance", "worst ever",
    "stupid", "idiotic",
]

SENSITIVE_FIELD_QUERY_TERMS = [
    "internal_score",
    "commission_amount",
    "seller_motivation",
    "seller's motivation",
    "owner_contact",
    "acquisition_strategy",
    "agent_performance_score",
]

GEOGRAPHY_LEAK_TERMS = [
    "new york", "los angeles", "london", "paris", "barcelona",
    "madrid", "berlin", "dubai", "singapore", "sydney",
    "toronto", "chicago", "miami", "boston",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blocked_response(reason: str, message: str) -> str:
    """Return a JSON-encoded blocked response string for wrap_tool_call."""
    return json.dumps({"status": "blocked", "reason": reason, "message": message})


def _blocked_exit(reason: str, message: str) -> dict[str, Any]:
    """Return the standard early-exit dict for before_agent / after_agent."""
    return {
        "messages": [AIMessage(_blocked_response(reason, message))],
        "jump_to": "end",
    }


def _redact_sensitive_fields(text: str) -> tuple[str, list[str]]:
    """TODO: Replace sensitive field values in tool output with [REDACTED].

    For each field name in SENSITIVE_FIELDS, use a regex to match the pattern:
      <field_name>: <value>
    and replace the value with [REDACTED].

    Pattern hint: r'(?i)(<field_name>)\\s*[:=][^\\n,]+'
    Replacement:  r'\\1: [REDACTED]'

    Returns:
      (cleaned_text, list_of_redacted_field_names)
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RealThorGuardrails(AgentMiddleware):
    """Three-layer guardrail middleware for RealThor v0.4.

    Layer 1 (before_agent): validates and filters incoming queries.
    Layer 2 (wrap_tool_call): enforces access control and redacts sensitive data.
    Layer 3 (after_agent): scans the final response for sensitive phrases.
    """

    # -------------------------------------------------------------------------
    # Layer 1 — Input guardrail
    # -------------------------------------------------------------------------

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """TODO: Implement input guardrail.

        Check the first human message in state["messages"] against the four
        input policies. Return _blocked_exit(...) for any violation.
        Return None if all checks pass (query is allowed through).

        Policies to enforce:
          - demographic_query      : query contains a term from DEMOGRAPHIC_TERMS
          - persona_escalation     : query contains a phrase from PERSONA_ESCALATION_PHRASES
          - topic_adherence        : query contains a term from TOPIC_DEVIATION_TERMS
          - geography_restriction  : query contains a term from GEOGRAPHY_TERMS
          - profanity_toxicity     : query contains a marker from PROFANITY_OUTPUT_MARKERS
          - sensitive_field_read   : query contains a term from SENSITIVE_FIELD_QUERY_TERMS

        Guard against:
          - Empty state["messages"] (return None)
          - Non-human first message (return None)
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Layer 2 — Tool/action guardrail
    # -------------------------------------------------------------------------

    def wrap_tool_call(self, request: Any, handler: Any) -> str:
        """TODO: Implement tool/action guardrail.

        Checks (in order):
          1. dataset_mutation          : tool_name in MUTATION_TOOLS → block for all roles
          2. broker_action_restriction : tool_name in ACTION_TOOLS AND role != "analyst"
          3. region_access             : tool_args.get("region") is set AND
                                         not user_ctx.can_access_region(region)

        For passing calls:
          - Call handler(request) to get the raw tool result (a string)
          - Call _redact_sensitive_fields(result) to strip sensitive values
          - If any fields were redacted, append a note:
              f"\\n[guardrail: sensitive_field_read — redacted: {', '.join(redacted)}]"
          - Return the (possibly redacted + annotated) result

        IMPORTANT: wrap_tool_call must return ToolMessage | Command — NOT a plain
        string. For blocked cases, wrap the JSON in a ToolMessage:

          from langchain_core.messages import ToolMessage
          return ToolMessage(
              content=_blocked_response(reason, msg),
              name=tool_name,
              tool_call_id=request.tool_call["id"],
          )

        Identity is in: request.runtime.context  (a UserContext instance)
        Tool name:      request.tool_call["name"]
        Tool args:      request.tool_call["args"] (dict)
        Tool call ID:   request.tool_call["id"]   (needed for ToolMessage)
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Layer 3 — Output guardrail
    # -------------------------------------------------------------------------

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """TODO: Implement output guardrail.

        Check the last message in state["messages"] against the three output
        policies. Return _blocked_exit(...) for any violation.
        Return None if the output is clean.

        Policies to enforce:
          - sensitive_content_output : output contains a phrase from SENSITIVE_OUTPUT_PHRASES
          - profanity_toxicity_output: output contains a marker from PROFANITY_OUTPUT_MARKERS
          - geography_leak           : output contains a term from GEOGRAPHY_LEAK_TERMS

        Guard against:
          - Empty state["messages"] (return None)
        """
        raise NotImplementedError
