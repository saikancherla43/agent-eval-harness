"""Entry point: run the eval harness and generate the report.

Usage:  python evals/run_evals.py
Writes: traces.jsonl, report.md, results.json  (all in the project root)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import run_harness      # noqa: E402
from mock_agent import mock_agent    # noqa: E402
from report import generate_report   # noqa: E402


def main():
    scenarios = json.loads((ROOT / "scenarios.json").read_text())
    runs = run_harness(scenarios, mock_agent, ROOT)
    results = generate_report(ROOT / "traces.jsonl",
                              ROOT / "report.md",
                              ROOT / "results.json")
    m = results["metrics"]
    print(f"Ran {m['n_runs']} scenarios against mock_agent.")
    print(f"  success rate:      {m['success_rate']:.2%} ({m['successes']}/{m['n_runs']})")
    print(f"  mean e2e latency:  {m['mean_e2e_latency_ms']:.1f} ms")
    print(f"  median e2e latency:{m['median_e2e_latency_ms']:.1f} ms")
    print(f"  mean steps/task:   {m['mean_steps_per_task']:.2f}")
    print(f"  tool error rate:   {m['tool_error_rate']:.2%} ({m['tool_errors']}/{m['tool_calls']})")
    print(f"  groundedness:      {m['groundedness_rate']:.2%} ({m['grounded_runs']}/{m['n_runs']})")
    print("Wrote traces.jsonl, report.md, results.json")


if __name__ == "__main__":
    main()
