"""Identity and state-isolation keys.

At scale, RealThor serves many callers at once. Two things must hold:

1. A caller's conversation must *persist* — a follow-up question continues the
   same thread instead of starting from nothing.
2. One caller's state must never *leak* into another's.

Both come down to a single rule: agent state is keyed to identity. This module
owns that key. ``resolve_user`` (already implemented for you) turns an
authenticated ``user_id`` into a ``UserContext`` read from the application
database, never trusted from the caller.

Your two TODOs:
  * ``thread_id_for`` — the checkpointer thread key every turn is keyed on.
  * ``trace_metadata`` — the identity attribution attached to each Langfuse trace.

``UserContext`` is defined in ``guardrails`` and re-exported here so identity has
one import surface.
"""

from realthor.guardrails import GUEST_CONTEXT, UserContext
from realthor.sessions import get_user

__all__ = [
    "GUEST_CONTEXT",
    "UserContext",
    "resolve_user",
    "thread_id_for",
    "trace_metadata",
]


def thread_id_for(user_id: str, session_id: str) -> str:
    """Derive the checkpointer thread key for a (user, session) pair.

    This is the third layer of RealThor's isolation contract, beneath
    authentication (you are who you logged in as) and session ownership (you can
    only resume your own sessions). Namespacing the thread by ``user_id`` means
    that even a leaked or guessed ``session_id`` cannot cross into another user's
    checkpoint space.

    Implement it so that:
      * Same ``user_id`` + same ``session_id`` → the same key (state resumes).
      * A different ``user_id`` *or* ``session_id`` → a different key (isolated).
      * An empty ``user_id`` is treated as ``"guest"``.

    A simple, readable string is enough — no hashing. The exact contract is in
    tests/test_context.py.
    """
    # TODO: return a deterministic key, unique per (user_id, session_id) and
    # namespaced by the user. Empty user_id → treat as "guest".
    raise NotImplementedError(
        "Implement thread_id_for — see the docstring and tests/test_context.py"
    )


def trace_metadata(user_ctx: UserContext, session_id: str, command: str) -> dict:
    """Build the Langfuse trace attribution for one run.

    This is the module's payoff wired into observability: every traced run is
    attributed to *who* ran it and *which session*, so in Langfuse you can filter
    by user or session and see each identity's runs as a separate group.

    Return a dict with the keys Langfuse reads from ``config["metadata"]``:
      * ``langfuse_user_id``    — ``user_ctx.user_id`` (or ``"guest"`` if empty),
      * ``langfuse_session_id`` — the ``session_id``,
      * ``langfuse_tags``       — ``[command]`` (e.g. ``["chat"]`` / ``["analyze"]``).

    The exact contract is in tests/test_context.py.
    """
    # TODO: return the langfuse_user_id / langfuse_session_id / langfuse_tags dict.
    raise NotImplementedError(
        "Implement trace_metadata — see the docstring and tests/test_context.py"
    )


def resolve_user(user_id: str, app_db_path: str) -> UserContext:
    """Resolve an identity to a ``UserContext`` from the application database.

    The role and region access come from the ``users`` table — never from a
    caller-supplied claim. Returns ``GUEST_CONTEXT`` when ``user_id`` is empty or
    unknown. Pre-provided; you do not need to change this.
    """
    if not user_id:
        return GUEST_CONTEXT
    row = get_user(app_db_path, user_id)
    if row is None:
        return GUEST_CONTEXT
    return UserContext(
        user_id=str(row["user_id"]),
        role=str(row["role"]),
        region_access=str(row["region_access"]),
    )
