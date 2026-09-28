"""Generate report.md + results.json from a traces.jsonl file."""

import json
from datetime import datetime, timezone

from metrics import compute_metrics


def generate_report(traces_path, report_md_path, results_json_path):
    with open(traces_path) as f:
        runs = [json.loads(line) for line in f if line.strip()]
    m = compute_metrics(runs)

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": m,
    }
    with open(results_json_path, "w") as f:
        json.dump(results, f, indent=2)

    tick = lambda b: "✓" if b else "✗"  # noqa: E731
    lines = [
        "# Agent eval run — report",
        "",
        f"Generated: {results['generated_at']}",
        f"Scenarios: {m['n_runs']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Task success rate | {m['success_rate']:.2%} ({m['successes']}/{m['n_runs']}) |",
        f"| Mean end-to-end latency | {m['mean_e2e_latency_ms']:.1f} ms |",
        f"| Median end-to-end latency | {m['median_e2e_latency_ms']:.1f} ms |",
        f"| Mean steps per task | {m['mean_steps_per_task']:.2f} |",
        f"| Tool calls | {m['tool_calls']} |",
        f"| Tool-call error rate | {m['tool_error_rate']:.2%} ({m['tool_errors']}/{m['tool_calls']}) |",
        f"| Groundedness (heuristic) | {m['groundedness_rate']:.2%} ({m['grounded_runs']}/{m['n_runs']}) |",
        f"| Mean claim coverage | {m['mean_claim_coverage']:.3f} |",
        f"| Total tokens (in/out, approx) | {m['total_tokens_in']} / {m['total_tokens_out']} |",
        "",
        "## Per-scenario results",
        "",
        "| Scenario | Success | Steps | E2E ms | Tool errors | Grounded | Claim coverage |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in m["per_scenario"]:
        lines.append(
            f"| {p['scenario_id']} | {tick(p['success'])} | {p['n_steps']} "
            f"| {p['e2e_latency_ms']:.1f} | {p['tool_errors']} "
            f"| {tick(p['grounded'])} | {p['claim_coverage']:.2f} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Latencies are measured wall-clock with `time.perf_counter()`; the mock",
        "  tools sleep fixed amounts (search 50 ms, weather 80 ms, calculator 10 ms)",
        "  so numbers are reproducible.",
        "- Token counts use a whitespace tokenizer and are approximate.",
        "- Groundedness is a substring-overlap heuristic, not a judge model: it",
        "  checks that the answer's key words appear in tool observations. It can",
        "  miss paraphrases and can pass answers that are faithful-but-wrong",
        "  (see `pricing-pro-year`).",
        "",
    ]
    with open(report_md_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return results
