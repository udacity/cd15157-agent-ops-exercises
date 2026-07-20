# RealThor Monitoring Report

## Summary

| Metric | Value |
|---|---|
| Total runs | 38 |
| Successes | 34 |
| Failures | 4 |
| Success rate | 89.5% |
| Avg latency | 3.06s |
| p95 latency | 7.08s |
| Total cost | $0.0123 |
| Avg cost per run | $0.0003 |
| Guardrail blocks | 5 |
| HITL approvals | 2 |
| HITL rejections | 1 |

## Tool Call Distribution

| Tool | Calls |
|---|---|
| get_listing_priority | 26 |
| get_supply_opportunities | 7 |
| submit_channel_recommendation | 3 |

## Common Failure Reasons

| Reason | Count |
|---|---|
| RateLimitError: rate limit exceeded | 2 |
| APITimeoutError: request timed out | 1 |
| APIConnectionError: connection reset | 1 |

## Key Signals

- p95 latency 7.08s exceeds 5s threshold
- failure rate 10.5% exceeds 10% threshold
