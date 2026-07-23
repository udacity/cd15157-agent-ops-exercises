"""Demo 2 — the *after*: log in, and your sessions are yours.

Same scenarios as demo_01, now correct:
  * login — a password proves identity before any context is resolved;
  * sessions — owned, resumable conversations with human-readable titles;
  * isolation — a caller can only see and resume their own sessions, and state
    is keyed by ``thread_id_for(user, session)`` so nothing leaks.

Run:  uv run python demo_02.py --case all
      uv run python demo_02.py --case login-sessions --trace   # attribute in Langfuse
      uv run python demo_02.py --case isolation                # ownership; no model call
"""

import click
from dotenv import load_dotenv

from realthor import auth, sessions
from realthor.agent import build_agent, build_checkpointer, build_tracer, ensure_db, run_turn
from realthor.config import load_config, resolve_paths

load_dotenv()
CONFIG = "config.yaml"


def _rule(title):
    click.echo("\n" + "=" * 60)
    click.echo(title)
    click.echo("=" * 60)


def case_login_sessions(cfg, trace):
    _rule("AFTER — login + an owned, resumable session")
    db = cfg["paths"]["app_db"]
    agent = build_agent(cfg, checkpointer=build_checkpointer(cfg))
    tracer = build_tracer(cfg) if trace else None

    # 1) Prove identity with a password (not a bare flag).
    click.echo("\nLogin: analyst_001 / <password>")
    ctx = auth.authenticate(db, "analyst_001", auth.DEV_PASSWORD)
    bad = auth.authenticate(db, "analyst_001", "wrong-password")
    click.echo(f"  correct password → {ctx.user_id} ({ctx.role})")
    click.echo(f"  wrong password   → {bad}  (denied)")

    # 2) Start a session; its title comes from the first message.
    first = "What's the demand for a 2-bedroom apartment in the west region?"
    title = sessions.generate_title(first)
    sid = sessions.create_session(db, ctx.user_id, title)
    click.echo(f'\nStarted session "{title}"')
    click.echo(f"  user> {first}")
    r1 = run_turn(agent, ctx, sid, first, tracer=tracer)
    sessions.touch_session(db, sid)
    click.echo(f"  realthor> {r1}")

    # 3) List and resume it — same user+session → same thread → it remembers.
    click.echo("\nYour sessions:")
    for s in sessions.list_sessions(db, ctx.user_id):
        click.echo(f"  · {s['title']}  ({s['message_count']} msgs)")
    resumed = sessions.get_session(db, sid, ctx.user_id)
    click.echo(f'\nResume "{resumed["title"]}":')
    click.echo("  user> Remind me which segment we were looking at.")
    r2 = run_turn(agent, ctx, sid, "Remind me which segment we were looking at.", tracer=tracer)
    sessions.touch_session(db, sid)
    click.echo(f"  realthor> {r2}")
    click.echo("\n→ Persisted, because the thread is keyed to (this user, this session).")
    if tracer:
        click.echo("(traced — filter Langfuse by user analyst_001 / this session)")


def case_isolation(cfg):
    _rule("AFTER — isolation: sessions belong to their owner")
    db = cfg["paths"]["app_db"]
    analyst = auth.authenticate(db, "analyst_001", auth.DEV_PASSWORD)
    broker = auth.authenticate(db, "broker_north_001", auth.DEV_PASSWORD)

    # analyst_001 owns a session; broker_north_001 must not see or resume it.
    sid = sessions.create_session(db, analyst.user_id, "Analyst private notes")
    click.echo(f"\nanalyst_001 created session {sid[:8]}… ('Analyst private notes')")

    click.echo("\nbroker_north_001 lists their sessions:")
    theirs = sessions.list_sessions(db, broker.user_id)
    click.echo(f"  → {[s['title'] for s in theirs]}  (analyst's is not here)")

    click.echo("\nbroker_north_001 tries to resume the analyst's session by id:")
    stolen = sessions.get_session(db, sid, broker.user_id)
    click.echo(f"  → get_session(...) = {stolen}  (ownership check denies it)")

    # One user, two sessions → different threads → no cross-talk.
    from realthor.context import thread_id_for
    s_west = sessions.create_session(db, analyst.user_id, "West focus")
    s_north = sessions.create_session(db, analyst.user_id, "North focus")
    click.echo("\nOne analyst, two sessions map to two isolated threads:")
    click.echo(f"  West  → {thread_id_for(analyst.user_id, s_west)}")
    click.echo(f"  North → {thread_id_for(analyst.user_id, s_north)}")
    click.echo("\n→ Isolation is identity-scoped state, not a smarter prompt.")


@click.command()
@click.option("--case", "case", default="all",
              type=click.Choice(["all", "login-sessions", "isolation"]))
@click.option("--trace/--no-trace", default=False, help="Attribute the run to user/session in Langfuse.")
def main(case, trace):
    cfg = resolve_paths(load_config(CONFIG), CONFIG)
    ensure_db(cfg)
    if case in ("all", "login-sessions"):
        case_login_sessions(cfg, trace)
    if case in ("all", "isolation"):
        case_isolation(cfg)


if __name__ == "__main__":
    main()
