"""Metric computation over saved traces. Every number comes from a real run.

Metrics:
- task success rate: fraction of scenarios whose final answer contains the
  expected answer
- mean / median end-to-end latency (ms, wall clock measured with perf_counter)
- mean steps per task
- tool-call error rate: tool_call steps with an error / all tool_call steps
- groundedness: % of runs whose final answer's key claims appear as
  substrings in the tool observations. This is a HEURISTIC PROXY for
  faithfulness, not a real judge model — it checks word overlap, so it can
  miss paraphrases and can pass answers that are faithful-but-wrong. A
  client engagement would add an LLM judge here.
"""

import re
import statistics

STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "are", "was", "were",
    "has", "have", "had", "this", "that", "from", "they", "them",
    "their", "will", "would", "there", "what", "when", "where", "which",
    "who", "whom", "how", "not", "but", "all", "any", "can", "her",
    "his", "she", "its", "our", "out", "about", "into", "over",
    "after", "before", "than", "then", "also", "just", "like", "more",
    "most", "such", "only", "own", "same", "too", "very", "may",
    "might", "must", "shall", "should", "could", "is", "it", "of",
    "in", "on", "to", "a", "an", "as", "at", "be", "by", "do",
}


def _norm(text):
    return re.sub(r"[^a-z0-9 ]", " ", str(text).lower())


def significant_words(text):
    return [w for w in _norm(text).split()
            if len(w) >= 3 and w not in STOPWORDS]


def claim_coverage(final_answer, observations_text):
    """Fraction of the answer's significant words found in the observations
    (whitespace-insensitive substring match). Returns (coverage, misses)."""
    words = significant_words(final_answer)
    if not words:
        return 1.0, []  # vacuous: no substantive claims to ground
    obs = _norm(observations_text).replace(" ", "")
    hits = [w for w in words if w in obs]
    misses = [w for w in words if w not in obs]
    return len(hits) / len(words), misses


def compute_metrics(runs, groundedness_threshold=0.5):
    n = len(runs)
    if n == 0:
        raise ValueError("no runs to score")

    successes = sum(1 for r in runs if r["success"])
    e2e = [r["e2e_latency_ms"] for r in runs]
    steps = [len(r["steps"]) for r in runs]
    tool_calls = [s for r in runs for s in r["steps"]
                  if s["type"] == "tool_call"]
    tool_errors = [s for s in tool_calls if s.get("error")]

    per_scenario = []
    grounded_count = 0
    coverages = []
    for r in runs:
        obs_text = " ".join(s.get("content", "") for s in r["steps"]
                            if s["type"] == "observation")
        coverage, _misses = claim_coverage(r.get("final_answer") or "", obs_text)
        grounded = coverage >= groundedness_threshold
        grounded_count += int(grounded)
        coverages.append(coverage)
        run_tool_calls = [s for s in r["steps"] if s["type"] == "tool_call"]
        per_scenario.append({
            "scenario_id": r["scenario_id"],
            "question": r["question"],
            "success": r["success"],
            "final_answer": r.get("final_answer"),
            "n_steps": len(r["steps"]),
            "e2e_latency_ms": r["e2e_latency_ms"],
            "tool_calls": len(run_tool_calls),
            "tool_errors": sum(1 for s in run_tool_calls if s.get("error")),
            "grounded": grounded,
            "claim_coverage": round(coverage, 3),
        })

    total_in = sum(s.get("tokens_in", 0) for r in runs for s in r["steps"])
    total_out = sum(s.get("tokens_out", 0) for r in runs for s in r["steps"])

    return {
        "n_runs": n,
        "successes": successes,
        "success_rate": round(successes / n, 4),
        "mean_e2e_latency_ms": round(statistics.mean(e2e), 2),
        "median_e2e_latency_ms": round(statistics.median(e2e), 2),
        "mean_steps_per_task": round(statistics.mean(steps), 2),
        "tool_calls": len(tool_calls),
        "tool_errors": len(tool_errors),
        "tool_error_rate": round(len(tool_errors) / len(tool_calls), 4)
        if tool_calls else 0.0,
        "grounded_runs": grounded_count,
        "groundedness_rate": round(grounded_count / n, 4),
        "mean_claim_coverage": round(statistics.mean(coverages), 3),
        "groundedness_threshold": groundedness_threshold,
        "total_tokens_in": total_in,
        "total_tokens_out": total_out,
        "per_scenario": per_scenario,
    }
