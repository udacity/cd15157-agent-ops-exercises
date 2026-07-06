import dataclasses
import json
from pathlib import Path


@dataclasses.dataclass
class RunRecord:
    run_id: str
    timestamp: str
    user_id: str
    command: str
    input_text: str
    success: bool
    failure_reason: str
    latency_s: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tools_called: list
    guardrail_blocked: bool
    guardrail_reason: str
    hitl_decision: str


@dataclasses.dataclass
class MonitoringMetrics:
    total_runs: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_s: float
    p95_latency_s: float
    total_cost_usd: float
    avg_cost_usd: float
    tool_call_counts: dict
    guardrail_block_count: int
    hitl_approval_count: int
    hitl_rejection_count: int
    common_failure_reasons: list


def load_run_records(log_path: Path) -> list:
    """Read JSONL log and return a list of RunRecord objects.

    If log_path does not exist, return an empty list.
    """
    raise NotImplementedError


def compute_metrics(records: list) -> MonitoringMetrics:
    """Aggregate a list of RunRecord objects into MonitoringMetrics.

    p95 latency: sort latency values and take the 95th percentile index.
    If fewer than 20 records, use max latency as the p95 fallback.

    tool_call_counts: flatten all tools_called lists and count occurrences.

    common_failure_reasons: group non-empty failure_reason values by count,
    return top 5 as list[tuple[str, int]].
    """
    raise NotImplementedError


def generate_report(metrics: MonitoringMetrics, output_dir: Path) -> None:
    """Write three report files to output_dir:

    monitoring_report.md — a summary table with all metrics plus a "Key signals"
    section that flags thresholds:
        - p95 latency > 5s
        - failure rate > 10%
        - avg cost per run > $0.05

    monitoring_report.json — dataclasses.asdict(metrics) as JSON.

    monitoring_report.html — self-contained HTML with the same metrics table and
    a CSS bar chart of tool call distribution. Color-coded Key Signals section
    (green when no thresholds exceeded, amber when any threshold fires).
    """
    raise NotImplementedError
