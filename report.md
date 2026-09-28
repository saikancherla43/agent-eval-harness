# Agent eval run — report

Generated: 2026-09-28T01:05:11.089607+00:00
Scenarios: 8

## Summary

| Metric | Value |
|---|---|
| Task success rate | 87.50% (7/8) |
| Mean end-to-end latency | 48.0 ms |
| Median end-to-end latency | 50.4 ms |
| Mean steps per task | 4.00 |
| Tool calls | 8 |
| Tool-call error rate | 12.50% (1/8) |
| Groundedness (heuristic) | 62.50% (5/8) |
| Mean claim coverage | 0.500 |
| Total tokens (in/out, approx) | 174 / 142 |

## Per-scenario results

| Scenario | Success | Steps | E2E ms | Tool errors | Grounded | Claim coverage |
|---|---|---|---|---|---|---|
| pricing-growth | ✓ | 4 | 52.0 | 0 | ✓ | 0.50 |
| math-percent | ✓ | 4 | 10.3 | 0 | ✗ | 0.00 |
| weather-berlin | ✓ | 4 | 80.2 | 0 | ✓ | 0.60 |
| sla | ✓ | 4 | 50.2 | 0 | ✓ | 1.00 |
| math-division | ✓ | 4 | 10.3 | 0 | ✗ | 0.00 |
| weather-unknown | ✓ | 4 | 80.3 | 1 | ✗ | 0.40 |
| refund | ✓ | 4 | 50.2 | 0 | ✓ | 1.00 |
| pricing-pro-year | ✗ | 4 | 50.5 | 0 | ✓ | 0.50 |

## Notes

- Latencies are measured wall-clock with `time.perf_counter()`; the mock
  tools sleep fixed amounts (search 50 ms, weather 80 ms, calculator 10 ms)
  so numbers are reproducible.
- Token counts use a whitespace tokenizer and are approximate.
- Groundedness is a substring-overlap heuristic, not a judge model: it
  checks that the answer's key words appear in tool observations. It can
  miss paraphrases and can pass answers that are faithful-but-wrong
  (see `pricing-pro-year`).

