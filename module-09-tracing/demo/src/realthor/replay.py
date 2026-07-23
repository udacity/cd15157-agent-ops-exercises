"""Reconstruct a past run from persisted checkpoints (+ an optional run log).

Self-contained demo version: reads checkpoints through the SqliteSaver API and,
if present, cross-references a minimal runs.jsonl for the input and the active
prompt/dataset version. No model, no API key needed to replay.
"""

import dataclasses
import json
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver


@dataclasses.dataclass
class ReplayContext:
    run_id: str
    input_text: str = ""
    prompt_version: str = ""
    dataset_version: str = ""
    tools_called: list = dataclasses.field(default_factory=list)
    intermediate_values: list = dataclasses.field(default_factory=list)
    final_output: str = ""
    restored: bool = False


def build_checkpointer(cfg: dict) -> SqliteSaver:
    conn = sqlite3.connect(cfg["debug"]["state_db"], check_same_thread=False)
    return SqliteSaver(conn)


def load_run(thread_id: str, checkpointer: SqliteSaver) -> list:
    config = {"configurable": {"thread_id": thread_id}}
    return list(reversed(list(checkpointer.list(config))))


def _log_row(run_id: str, log_path: Path) -> dict | None:
    if not log_path.exists():
        return None
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line and json.loads(line).get("run_id") == run_id:
                return json.loads(line)
    return None


def reconstruct_context(run_id: str, checkpointer: SqliteSaver, log_path: Path) -> ReplayContext:
    ctx = ReplayContext(run_id=run_id)
    snapshots = load_run(run_id, checkpointer)
    ctx.restored = bool(snapshots)

    if snapshots:
        messages = snapshots[-1].checkpoint.get("channel_values", {}).get("messages", [])
        for msg in messages:
            if isinstance(msg, ToolMessage):
                if msg.name:
                    ctx.tools_called.append(msg.name)
                ctx.intermediate_values.append(str(msg.content))
            elif isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content:
                ctx.final_output = msg.content

    row = _log_row(run_id, log_path)
    if row:
        ctx.input_text = row.get("input_text", "")
        ctx.prompt_version = row.get("prompt_version", "")
        ctx.dataset_version = row.get("dataset_version", "")

    return ctx


def format_report(ctx: ReplayContext) -> str:
    trajectory = " → ".join(ctx.tools_called) if ctx.tools_called else "(none)"
    lines = [
        f"Replay of run {ctx.run_id}",
        f"  state restored : {ctx.restored}",
        f"  input          : {ctx.input_text}",
        f"  prompt version : {ctx.prompt_version or '(unknown)'}",
        f"  dataset version: {ctx.dataset_version or '(unknown)'}",
        f"  tool trajectory: {trajectory}",
    ]
    for name, value in zip(ctx.tools_called, ctx.intermediate_values):
        lines.append(f"    - {name}: {value}")
    lines.append(f"  final output   : {ctx.final_output}")
    return "\n".join(lines)
