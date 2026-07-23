import json
from dataclasses import dataclass

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, ToolMessage


# ---------------------------------------------------------------------------
# Identity context — resolved from users.csv, never from user message
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
# Policy word lists
# ---------------------------------------------------------------------------

PERSONA_ESCALATION_PHRASES = [
    "pretend you are", "act as analyst", "ignore your role",
    "forget your instructions", "you are now", "with full access",
]

TOPIC_DEVIATION_TERMS = [
    "who won", "who is winning", "who beat", "score of",
    "world cup", "soccer", "football", "nba", "basketball", 
    "stock", "weather", "forecast", "python", "recipe", 
    "news", "celebrity", "movie", "music", "tips", "review",
]

ACTION_TOOLS = {"flag_segment_for_review", "create_segment_report"}

# Reasons that must terminate the run — the model must not fall back to a
# different tool call to work around the block. Extend this set when adding
# new user-context access restrictions.
TERMINAL_ACCESS_REASONS = {"region_access"}

SENSITIVE_OUTPUT_PHRASES = [
    "demographic transition",
    "underserved area",
    "underserved neighborhood",
    "minority neighborhood",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _blocked(reason: str, message: str) -> dict:
    return {
        "messages": [AIMessage(json.dumps({
            "status": "blocked",
            "reason": reason,
            "message": message,
        }))],
        "jump_to": "end",
    }


# ---------------------------------------------------------------------------
# Layer 1 — Input guardrail
# ---------------------------------------------------------------------------

class InputGuardrails(AgentMiddleware):
    """Block prohibited queries before the agent runs."""

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state, runtime):
        if not state["messages"]:
            return None
        query = state["messages"][0].content.lower()

        if any(p in query for p in PERSONA_ESCALATION_PHRASES):
            return _blocked(
                "persona_escalation",
                "Role escalation is not permitted. "
                "Your access level is determined by your account, not by the query.",
            )

        if any(t in query for t in TOPIC_DEVIATION_TERMS):
            return _blocked(
                "topic_adherence",
                "RealThor answers Ciudaty listing intelligence questions only.",
            )

        return None


# ---------------------------------------------------------------------------
# Layer 2 — Tool/access guardrail
# ---------------------------------------------------------------------------

class ToolGuardrails(AgentMiddleware):
    """Enforce role-based access on tool calls.

    wrap_tool_call blocks the individual tool call and records the reason in
    the ToolMessage. before_model fires before each model iteration; if any
    blocked ToolMessage in the history has a reason in TERMINAL_ACCESS_REASONS,
    it terminates the run — preventing the model from falling back to a
    different tool call to work around the block.
    """

    def wrap_tool_call(self, request, handler):
        user_ctx: UserContext = request.runtime.context
        tool_name: str = request.tool_call["name"]
        tool_args: dict = request.tool_call["args"]
        tool_call_id: str = request.tool_call["id"]
        region = tool_args.get("region", "")

        if region and not user_ctx.can_access_region(region):
            return ToolMessage(
                content=json.dumps({
                    "status": "blocked",
                    "reason": "region_access",
                    "message": (
                        f"Access denied for region '{region}'. "
                        f"Your account covers: {user_ctx.region_access or 'none'}."
                    ),
                }),
                name=tool_name,
                tool_call_id=tool_call_id,
            )

        if tool_name in ACTION_TOOLS and user_ctx.role != "analyst":
            return ToolMessage(
                content=json.dumps({
                    "status": "blocked",
                    "reason": "broker_action_restriction",
                    "message": (
                        f"'{tool_name}' is restricted to internal analysts. "
                        "Brokers and guests cannot initiate internal workflows."
                    ),
                }),
                name=tool_name,
                tool_call_id=tool_call_id,
            )

        return handler(request)

    @hook_config(can_jump_to=["end"])
    def before_model(self, state, runtime):
        """Terminate the run if any terminal access block is in the message history."""
        for msg in state.get("messages", []):
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                try:
                    payload = json.loads(msg.content)
                    if payload.get("reason") in TERMINAL_ACCESS_REASONS:
                        return _blocked(payload["reason"], payload.get("message", "Access denied."))
                except (json.JSONDecodeError, AttributeError):
                    pass
        return None


# ---------------------------------------------------------------------------
# Layer 3 — Output guardrail
# ---------------------------------------------------------------------------

class OutputGuardrails(AgentMiddleware):
    """Block sensitive content in the final response."""

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state, runtime):
        if not state["messages"]:
            return None
        output = state["messages"][-1].content.lower()

        if any(phrase in output for phrase in SENSITIVE_OUTPUT_PHRASES):
            return _blocked(
                "sensitive_content_output",
                "The response contained restricted content and was blocked. "
                "Please rephrase your question to focus on market signals.",
            )

        return None
