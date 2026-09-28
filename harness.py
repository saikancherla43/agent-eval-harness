"""Scenario runner: executes scripted scenarios against an agent callable.

The agent callable must have the signature ``agent_fn(scenario, tracer) -> str``
where ``scenario`` is one dict from scenarios.json and ``tracer`` is a
``Tracer`` the agent uses to log its steps. End-to-end latency is measured
around the agent call with time.perf_counter().
"""

import json
import time
from pathlib import Path

from tracer import Tracer


def check_success(final_answer, expected_answer):
    """A scenario passes if the expected answer appears in the final answer
    (case-insensitive substring). Simple, transparent, and adequate for a
    scripted mock; a client engagement would swap in exact-match or an
    LLM judge here."""
    return expected_answer.lower() in (final_answer or "").lower()


def run_harness(scenarios, agent_fn, out_dir):
    """Run every scenario, return the list of run dicts, save traces.jsonl."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tracer = Tracer()
    for i, sc in enumerate(scenarios, start=1):
        tracer.start_run(run_id=f"run-{i:02d}",
                         scenario_id=sc["id"],
                         question=sc["question"])
        t0 = time.perf_counter()
        final_answer = agent_fn(sc, tracer)
        e2e_ms = (time.perf_counter() - t0) * 1000
        tracer.end_run(final_answer,
                       check_success(final_answer, sc["expected_answer"]),
                       e2e_ms)
    traces_path = out_dir / "traces.jsonl"
    tracer.save_jsonl(traces_path)
    return tracer.runs
