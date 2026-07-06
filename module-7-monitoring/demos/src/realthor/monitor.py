import dataclasses
import json
from collections import Counter
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
    if not log_path.exists():
        return []
    records = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            records.append(RunRecord(**data))
    return records


def compute_metrics(records: list) -> MonitoringMetrics:
    total = len(records)
    if total == 0:
        return MonitoringMetrics(
            total_runs=0,
            success_count=0,
            failure_count=0,
            success_rate=0.0,
            avg_latency_s=0.0,
            p95_latency_s=0.0,
            total_cost_usd=0.0,
            avg_cost_usd=0.0,
            tool_call_counts={},
            guardrail_block_count=0,
            hitl_approval_count=0,
            hitl_rejection_count=0,
            common_failure_reasons=[],
        )

    success_count = sum(1 for r in records if r.success)
    failure_count = total - success_count
    success_rate = success_count / total

    latencies = sorted(r.latency_s for r in records)
    avg_latency_s = sum(latencies) / total
    if total >= 20:
        p95_idx = int(total * 0.95) - 1
        p95_latency_s = latencies[max(0, p95_idx)]
    else:
        p95_latency_s = latencies[-1]

    total_cost_usd = sum(r.cost_usd for r in records)
    avg_cost_usd = total_cost_usd / total

    all_tools = [tool for r in records for tool in r.tools_called]
    tool_call_counts = dict(Counter(all_tools))

    guardrail_block_count = sum(1 for r in records if r.guardrail_blocked)
    hitl_approval_count = sum(1 for r in records if r.hitl_decision == "approved")
    hitl_rejection_count = sum(1 for r in records if r.hitl_decision == "rejected")

    reasons = [r.failure_reason for r in records if r.failure_reason]
    reason_counts = Counter(reasons)
    common_failure_reasons = reason_counts.most_common(5)

    return MonitoringMetrics(
        total_runs=total,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=success_rate,
        avg_latency_s=avg_latency_s,
        p95_latency_s=p95_latency_s,
        total_cost_usd=total_cost_usd,
        avg_cost_usd=avg_cost_usd,
        tool_call_counts=tool_call_counts,
        guardrail_block_count=guardrail_block_count,
        hitl_approval_count=hitl_approval_count,
        hitl_rejection_count=hitl_rejection_count,
        common_failure_reasons=common_failure_reasons,
    )


def generate_report(metrics: MonitoringMetrics, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    failure_rate = 1.0 - metrics.success_rate if metrics.total_runs > 0 else 0.0

    signals = []
    if metrics.p95_latency_s > 5.0:
        signals.append(f"- p95 latency {metrics.p95_latency_s:.2f}s exceeds 5s threshold")
    if failure_rate > 0.10:
        signals.append(f"- failure rate {failure_rate:.1%} exceeds 10% threshold")
    if metrics.avg_cost_usd > 0.05:
        signals.append(f"- avg cost per run ${metrics.avg_cost_usd:.4f} exceeds $0.05 threshold")

    tool_rows = "\n".join(
        f"| {name} | {count} |"
        for name, count in sorted(metrics.tool_call_counts.items(), key=lambda x: -x[1])
    ) or "| — | — |"

    failure_rows = "\n".join(
        f"| {reason} | {count} |"
        for reason, count in metrics.common_failure_reasons
    ) or "| — | — |"

    md = f"""# RealThor Monitoring Report

## Summary

| Metric | Value |
|---|---|
| Total runs | {metrics.total_runs} |
| Successes | {metrics.success_count} |
| Failures | {metrics.failure_count} |
| Success rate | {metrics.success_rate:.1%} |
| Avg latency | {metrics.avg_latency_s:.2f}s |
| p95 latency | {metrics.p95_latency_s:.2f}s |
| Total cost | ${metrics.total_cost_usd:.4f} |
| Avg cost per run | ${metrics.avg_cost_usd:.4f} |
| Guardrail blocks | {metrics.guardrail_block_count} |
| HITL approvals | {metrics.hitl_approval_count} |
| HITL rejections | {metrics.hitl_rejection_count} |

## Tool Call Distribution

| Tool | Calls |
|---|---|
{tool_rows}

## Common Failure Reasons

| Reason | Count |
|---|---|
{failure_rows}

## Key Signals

"""
    if signals:
        md += "\n".join(signals) + "\n"
    else:
        md += "No thresholds exceeded.\n"

    md_path = output_dir / "monitoring_report.md"
    md_path.write_text(md)

    json_path = output_dir / "monitoring_report.json"
    json_path.write_text(json.dumps(dataclasses.asdict(metrics), indent=2))
