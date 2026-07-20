from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage, ToolMessage
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
        if self.region_access == "all":
            return True
        return region in self.region_access.split("|")


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

# Reasons that must terminate the run — the model must not fall back to a
# different tool call to work around the block. Extend this set when adding
# new user-context access restrictions. Pre-provided: before_model reads it.
TERMINAL_ACCESS_REASONS = {"region_access", "dataset_mutation", "broker_action_restriction"}


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
    """Return a JSON-encoded blocked response string (used inside a ToolMessage)."""
    return json.dumps({"status": "blocked", "reason": reason, "message": message})


def _redact_sensitive_fields(text: str) -> tuple[str, list[str]]:
    """Strip sensitive field values from tool output. Returns (cleaned_text, redacted_fields)."""
    redacted = []
    for field in SENSITIVE_FIELDS:
        pattern = rf"(?i)({re.escape(field)})\s*[:=][^\n,]+"
        if re.search(pattern, text):
            text = re.sub(pattern, rf"\1: [REDACTED]", text)
            redacted.append(field)
    return text, redacted


# ---------------------------------------------------------------------------
# Layer 1 — Input guardrail
# ---------------------------------------------------------------------------

class InputGuardrails(AgentMiddleware):
    """Block prohibited queries before the agent runs."""

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """TODO: Implement input guardrail.

        Check the first human message in state["messages"] against the six
        input policies. On a violation, return a jump-to-end dict wrapping
        _blocked_response(reason, message) in an AIMessage:
            {"messages": [AIMessage(_blocked_response(reason, message))], "jump_to": "end"}
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


# ---------------------------------------------------------------------------
# Layer 2 — Tool/access guardrail
# ---------------------------------------------------------------------------

class ToolGuardrails(AgentMiddleware):
    """Enforce role-based access on tool calls and redact sensitive fields.

    wrap_tool_call blocks the individual tool call and records the reason in
    the ToolMessage. before_model (pre-provided) fires before each model
    iteration; if any blocked ToolMessage in the history has a reason in
    TERMINAL_ACCESS_REASONS, it terminates the run before the model can fall
    back to a different tool call to work around the block.
    """

    def wrap_tool_call(self, request: Any, handler: Callable) -> Any:
        """TODO: Implement tool/access guardrail.

        Extract identity and tool info at the top of the method:
          tool_name    = request.tool_call["name"]
          tool_call_id = request.tool_call["id"]
          ctx          = request.runtime.context      # UserContext
          tool_args    = request.tool_call["args"]

        Checks (in order):
          1. dataset_mutation          : tool_name in MUTATION_TOOLS → block for all roles
          2. broker_action_restriction : tool_name in ACTION_TOOLS AND ctx.role != "analyst"
          3. region_access             : tool_args.get("region") is set AND
                                         not ctx.can_access_region(region)

        Blocked cases must return a ToolMessage (NOT a plain string):
          return ToolMessage(
              content=_blocked_response(reason, msg),
              name=tool_name,
              tool_call_id=tool_call_id,
          )

        For passing calls:
          - result = handler(request)   # a ToolMessage
          - cleaned, redacted = _redact_sensitive_fields(result.content)
          - if redacted, return a new ToolMessage with cleaned content plus:
              f"\\n[guardrail: sensitive_field_read — blocked fields: {', '.join(redacted)}]"
          - otherwise return the original result unchanged
        """
        raise NotImplementedError

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """Terminate the run if any terminal access block is in the message history.

        Pre-provided. wrap_tool_call records a blocked ToolMessage (required so
        OpenAI sees a response for every tool_call_id); this hook detects a
        terminal reason in the history and stops before the model can retry.
        """
        for msg in state.get("messages", []):
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                try:
                    payload = json.loads(msg.content)
                    if payload.get("reason") in TERMINAL_ACCESS_REASONS:
                        return {
                            "messages": [AIMessage(_blocked_response(
                                payload["reason"],
                                payload.get("message", "Access denied."),
                            ))],
                            "jump_to": "end",
                        }
                except (json.JSONDecodeError, AttributeError):
                    pass
        return None


# ---------------------------------------------------------------------------
# Layer 3 — Output guardrail
# ---------------------------------------------------------------------------

class OutputGuardrails(AgentMiddleware):
    """Block sensitive content in the final response."""

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """TODO: Implement output guardrail.

        Check the last message in state["messages"] against the three output
        policies. On a violation, return a jump-to-end dict wrapping
        _blocked_response(reason, message) in an AIMessage:
            {"messages": [AIMessage(_blocked_response(reason, message))], "jump_to": "end"}
        Return None if the output is clean.

        Policies to enforce:
          - sensitive_content_output : output contains a phrase from SENSITIVE_OUTPUT_PHRASES
          - profanity_toxicity_output: output contains a marker from PROFANITY_OUTPUT_MARKERS
          - geography_leak           : output contains a term from GEOGRAPHY_LEAK_TERMS

        Guard against:
          - Empty state["messages"] (return None)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Convenience — pass this list to create_agent(middleware=...)
# ---------------------------------------------------------------------------

def make_guardrails() -> list[AgentMiddleware]:
    """Return the three guardrail layers in order."""
    return [InputGuardrails(), ToolGuardrails(), OutputGuardrails()]
