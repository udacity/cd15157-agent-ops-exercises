"""Identity and the state-isolation key (demo).

``thread_id_for`` is the whole point of the module: it derives the checkpointer
thread key from a (user, session) pair so the same identity+session resumes its
own conversation and no other identity can reach it. ``resolve_user`` turns an
authenticated ``user_id`` into a ``UserContext`` read from the database, never
from the caller.
"""

from dataclasses import dataclass

from realthor.sessions import get_user


@dataclass
class UserContext:
    user_id: str = ""
    role: str = "guest"
    region_access: str = ""  # "all" for analysts; single/pipe-separated for brokers

    def can_access_region(self, region: str) -> bool:
        if self.region_access == "all":
            return True
        return region in self.region_access.split("|")


GUEST_CONTEXT = UserContext()


def thread_id_for(user_id: str, session_id: str) -> str:
    """Checkpointer thread key, namespaced by user.

    Same user+session → same key (state resumes). Different user *or* session →
    different key (state isolated). The ``user_id`` prefix means a leaked
    ``session_id`` still cannot cross into another user's checkpoint space.
    """
    return f"{user_id or 'guest'}:{session_id}"


def resolve_user(user_id: str, app_db_path: str) -> UserContext:
    """Resolve identity from the users table. Guest if empty/unknown."""
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
