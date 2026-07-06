"""Reconstruct a past agent run from persisted checkpoints + the run log.

Debugging in a non-deterministic system starts with reproducibility: you cannot
fix a failure you cannot restore. This module reads the durable SqliteSaver
checkpoints written during a run (keyed by thread_id == run_id) and cross-references
the monitoring log to rebuild the run's execution context.

It reads state through the checkpointer's own API, so it needs no model, no API
key, and no dataset load — a run can be inspected long after the process that
produced it has exited.

>>> YOUR TASK: implement the three functions marked TODO. The dataclass and the
report formatter are provided. Run `uv run pytest tests/test_replay.py -v`.
"""

import dataclasses
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from realthor.monitor import load_run_records


@dataclasses.dataclass
class ReplayContext:
    """The reconstructed execution context of a single run."""

    run_id: str
    input_text: str = ""
    prompt_version: str = ""
    dataset_version: str = ""
    tools_called: list = dataclasses.field(default_factory=list)
    intermediate_values: list = dataclasses.field(default_factory=list)
    final_output: str = ""
    restored: bool = False


def build_checkpointer(cfg: dict) -> SqliteSaver:
    """TODO 1 — open the durable checkpoint database as a SqliteSaver.

    Use the plain constructor with a raw sqlite3 connection so the saver stays
    alive for the whole command (unlike ``from_conn_string``, whose connection
    closes on ``with``-block exit). Pass ``check_same_thread=False`` so the agent
    loop can touch the connection from worker threads.

    The DB path is at cfg["debug"]["state_db"].
    """
    raise NotImplementedError("Implement build_checkpointer")


def load_run(thread_id: str, checkpointer: SqliteSaver) -> list:
    """TODO 2 — return the run's checkpoint tuples, oldest to newest.

    ``checkpointer.list(config)`` yields tuples most-recent-first, where config is
    ``{"configurable": {"thread_id": thread_id}}``. Reverse so the caller reads the
    run in execution order. Return an empty list if the thread was never persisted.
    """
    raise NotImplementedError("Implement load_run")


def reconstruct_context(run_id: str, checkpointer: SqliteSaver, log_path: Path) -> ReplayContext:
    """TODO 3 — rebuild the execution context for ``run_id``.

    Steps:
      1. snapshots = load_run(run_id, checkpointer); restored = bool(snapshots)
      2. From the newest snapshot's messages
         (snapshot.checkpoint["channel_values"]["messages"]):
           - ToolMessage.name -> tools_called
           - ToolMessage.content -> intermediate_values (use _as_text)
           - last non-empty AIMessage.content -> final_output
      3. Cross-reference the runs.jsonl row for run_id via load_run_records:
         copy input_text, prompt_version, dataset_version; if no tools were found
         in state, fall back to the record's tools_called.
      4. Return the ReplayContext.
    """
    raise NotImplementedError("Implement reconstruct_context")


def _as_text(content) -> str:
    """Normalize message content (str or content-block list) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [c.get("text", "") if isinstance(c, dict) else str(c) for c in content]
        return "".join(parts)
    return str(content)


def format_report(ctx: ReplayContext) -> str:
    """Render a reconstructed run as a human-readable report."""
    trajectory = " → ".join(ctx.tools_called) if ctx.tools_called else "(none)"
    lines = [
        f"Replay of run {ctx.run_id}",
        f"  state restored : {ctx.restored}",
        f"  input          : {ctx.input_text}",
        f"  prompt version : {ctx.prompt_version or '(unknown)'}",
        f"  dataset version: {ctx.dataset_version or '(unknown)'}",
        f"  tool trajectory: {trajectory}",
    ]
    if ctx.intermediate_values:
        lines.append("  intermediate values:")
        for name, value in zip(ctx.tools_called, ctx.intermediate_values):
            lines.append(f"    - {name}: {value}")
    lines.append(f"  final output   : {ctx.final_output}")
    return "\n".join(lines)
