import dataclasses
import json
from datetime import datetime, timezone
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


def _generate_html(metrics: MonitoringMetrics) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    failure_rate = 1.0 - metrics.success_rate if metrics.total_runs > 0 else 0.0

    if metrics.tool_call_counts:
        max_calls = max(metrics.tool_call_counts.values())
        sorted_tools = sorted(metrics.tool_call_counts.items(), key=lambda x: -x[1])
        tool_chart = "".join(
            f'<div class="bar-row">'
            f'<div class="bar-label" title="{name}">{name}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{int(count/max_calls*100)}%"></div></div>'
            f'<div class="bar-count">{count}</div>'
            f'</div>\n'
            for name, count in sorted_tools
        )
    else:
        tool_chart = '<p class="empty">No tool calls recorded.</p>'

    signal_items = []
    if metrics.p95_latency_s > 5.0:
        signal_items.append(f"p95 latency {metrics.p95_latency_s:.2f}s exceeds 5s threshold")
    if failure_rate > 0.10:
        signal_items.append(f"failure rate {failure_rate:.1%} exceeds 10% threshold")
    if metrics.avg_cost_usd > 0.05:
        signal_items.append(f"avg cost per run ${metrics.avg_cost_usd:.4f} exceeds $0.05 threshold")

    if signal_items:
        items_html = "".join(f'<div class="signal-item">&#9888; {s}</div>' for s in signal_items)
        signals_html = f'<div class="signals warn">{items_html}</div>'
    else:
        signals_html = '<div class="signals ok">No thresholds exceeded.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>RealThor Monitoring Report</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1.25rem; color: #1f2937; }}
    h1 {{ font-size: 1.35rem; font-weight: 700; margin-bottom: 0.2rem; }}
    .meta {{ color: #6b7280; font-size: 0.875rem; margin-bottom: 2rem; }}
    h2 {{ font-size: 1rem; font-weight: 600; margin: 2rem 0 0.75rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.35rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 0.5rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.75rem; border-bottom: 1px solid #f3f4f6; font-size: 0.9rem; }}
    th {{ background: #f9fafb; font-weight: 600; color: #374151; }}
    .bar-row {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.35rem; }}
    .bar-label {{ width: 220px; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #374151; }}
    .bar-track {{ flex: 1; background: #f3f4f6; border-radius: 4px; height: 14px; }}
    .bar-fill {{ background: #3b82f6; height: 100%; border-radius: 4px; min-width: 2px; }}
    .bar-count {{ font-size: 0.85rem; color: #6b7280; min-width: 2rem; text-align: right; }}
    .signals {{ padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.9rem; }}
    .signals.ok {{ background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }}
    .signals.warn {{ background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }}
    .signal-item {{ margin: 0.2rem 0; }}
    .empty {{ color: #9ca3af; font-size: 0.875rem; font-style: italic; }}
  </style>
</head>
<body>
  <h1>RealThor Monitoring Report</h1>
  <div class="meta">{metrics.total_runs} runs &middot; generated {timestamp}</div>

  <h2>Summary</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Total runs</td><td>{metrics.total_runs}</td></tr>
    <tr><td>Successes</td><td>{metrics.success_count}</td></tr>
    <tr><td>Failures</td><td>{metrics.failure_count}</td></tr>
    <tr><td>Success rate</td><td>{metrics.success_rate:.1%}</td></tr>
    <tr><td>Avg latency</td><td>{metrics.avg_latency_s:.2f}s</td></tr>
    <tr><td>p95 latency</td><td>{metrics.p95_latency_s:.2f}s</td></tr>
    <tr><td>Total cost</td><td>${metrics.total_cost_usd:.4f}</td></tr>
    <tr><td>Avg cost per run</td><td>${metrics.avg_cost_usd:.4f}</td></tr>
    <tr><td>Guardrail blocks</td><td>{metrics.guardrail_block_count}</td></tr>
    <tr><td>HITL approvals</td><td>{metrics.hitl_approval_count}</td></tr>
    <tr><td>HITL rejections</td><td>{metrics.hitl_rejection_count}</td></tr>
  </table>

  <h2>Tool Call Distribution</h2>
  {tool_chart}
  <h2>Key Signals</h2>
  {signals_html}
</body>
</html>"""


def generate_report(metrics: MonitoringMetrics, output_dir: Path) -> None:
    """Write three report files to output_dir:

    monitoring_report.md: a summary table with all metrics plus a "Key signals"
    section that flags thresholds:
        - p95 latency > 5s
        - failure rate > 10%
        - avg cost per run > $0.05

    monitoring_report.json: dataclasses.asdict(metrics) as JSON.

    monitoring_report.html: the HTML renderer _generate_html(metrics) is
    pre-provided above. Write its return value to monitoring_report.html; you do
    not implement the HTML yourself.
    """
    raise NotImplementedError
