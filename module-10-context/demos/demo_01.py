"""Demo 1 — the *before*: a flag is not a login, a run is not a session.

Reproduces the two failures RealThor has before this module:
  * impersonation — identity is a bare ``--user`` claim, no password;
  * amnesia — every run gets a fresh thread, so nothing is remembered, and the
    naive fix (share a thread) leaks one caller's context into another's.

Run:  uv run python demo_01.py --case all
      uv run python demo_01.py --case impersonation   # no model call
      uv run python demo_01.py --case amnesia
"""

import click
from dotenv import load_dotenv

from realthor.agent import build_agent, build_checkpointer, ensure_db, run_turn_raw
from realthor.config import load_config, resolve_paths
from realthor.context import UserContext, resolve_user

load_dotenv()
CONFIG = "config.yaml"


def _rule(title):
    click.echo("\n" + "=" * 60)
    click.echo(title)
    click.echo("=" * 60)


def case_impersonation(cfg):
    _rule("BEFORE — impersonation: a flag is not a login")
    db = cfg["paths"]["app_db"]

    # The old CLI trusted --user with no password. Anyone can pick any id.
    ctx = resolve_user("analyst_001", db)
    click.echo(f"$ realthor chat --user analyst_001   (no password asked)")
    click.echo(f"  → became {ctx.user_id}: role={ctx.role}, region_access={ctx.region_access}")

    # Worse, a flag can carry anything the caller invents — nothing verifies it.
    forged = UserContext(user_id="ceo_root", role="admin", region_access="all")
    click.echo(f"$ realthor chat --user ceo_root       (also no password)")
    click.echo(f"  → claimed {forged.user_id}: role={forged.role}, region_access={forged.region_access}")
    click.echo("\nNo credential was ever checked. Identity is unproven.")


def case_amnesia(cfg):
    _rule("BEFORE — amnesia: every run is a throwaway thread")
    agent = build_agent(cfg, checkpointer=build_checkpointer(cfg))
    analyst = resolve_user("analyst_001", cfg["paths"]["app_db"])

    # Two turns, each on a FRESH random thread — the second forgets the first.
    import uuid
    click.echo("\nTurn 1 (thread A):")
    click.echo("  user> For my notes: my client's acquisition budget is 2.4 million euros.")
    r1 = run_turn_raw(agent, analyst, str(uuid.uuid4()), "For my notes: my client's acquisition budget is 2.4 million euros.")
    click.echo(f"  realthor> {r1}")
    click.echo("\nTurn 2 (thread B — a new run):")
    click.echo("  user> What budget did we just discuss?")
    r2 = run_turn_raw(agent, analyst, str(uuid.uuid4()), "What budget did we just discuss?")
    click.echo(f"  realthor> {r2}")
    click.echo("\n→ No memory across runs. There is no session.")

    # Naive fix: share one hardcoded thread so it 'remembers'. Now it leaks.
    _rule("BEFORE — the naive fix leaks: one shared thread, two users")
    broker = resolve_user("broker_north_001", cfg["paths"]["app_db"])
    shared = "shared-thread"
    a_msg = "For my notes: my client's acquisition budget is 2.4 million euros."
    click.echo("\nUser A = analyst_001 (thread 'shared-thread'):")
    click.echo(f"  user> {a_msg}")
    a_reply = run_turn_raw(agent, analyst, shared, a_msg)
    click.echo(f"  realthor> {a_reply}")
    click.echo("\nUser B = broker_north_001 (SAME thread 'shared-thread'):")
    click.echo("  user> What budget did we discuss earlier?")
    leak = run_turn_raw(agent, broker, shared, "What budget did we discuss earlier?")
    click.echo(f"  realthor> {leak}")
    click.echo("\n→ User B just read User A's private note. State is shared because nothing keys it to identity.")


@click.command()
@click.option("--case", "case", default="all",
              type=click.Choice(["all", "impersonation", "amnesia"]))
def main(case):
    cfg = resolve_paths(load_config(CONFIG), CONFIG)
    ensure_db(cfg)
    if case in ("all", "impersonation"):
        case_impersonation(cfg)
    if case in ("all", "amnesia"):
        case_amnesia(cfg)


if __name__ == "__main__":
    main()
