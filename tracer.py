"""Structured trace logging for agent runs. Standard library only.

Every run records an ordered list of steps. Step schema:
    {
        "step_id": int,
        "type": "reason" | "tool_call" | "observation" | "final",
        "tool_name": str | None,
        "content": str,            # what happened (args, reasoning text, observation, answer)
        "latency_ms": float,       # measured with time.perf_counter()
        "tokens_in": int,          # approximate, whitespace tokenizer
        "tokens_out": int,         # approximate, whitespace tokenizer
        "error": str | None,       # e.g. "ValueError: no weather data for 'Atlantis'"
        "timestamp": str,          # ISO-8601 UTC
    }

Token counts use a simple whitespace split. This is documented as
APPROXIMATE: real tokenizers (tiktoken, etc.) produce different counts,
but whitespace is a fine proxy for relative cost comparisons and it keeps
the harness dependency-free.
"""

import json
import time
from datetime import datetime, timezone


def count_tokens(text):
    """Approximate token count via whitespace splitting."""
    if not text:
        return 0
    return len(str(text).split())


def _now():
    return datetime.now(timezone.utc).isoformat()


class Tracer:
    def __init__(self):
        self.runs = []
        self._current = None
        self._step_id = 0

    # -- run lifecycle -------------------------------------------------
    def start_run(self, run_id, scenario_id, question):
        self._current = {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "question": question,
            "started_at": _now(),
            "steps": [],
            "final_answer": None,
            "success": None,
            "e2e_latency_ms": None,
        }
        self._step_id = 0

    def end_run(self, final_answer, success, e2e_latency_ms):
        assert self._current is not None, "start_run() must be called first"
        self._current["final_answer"] = final_answer
        self._current["success"] = bool(success)
        self._current["e2e_latency_ms"] = round(e2e_latency_ms, 3)
        self._current["ended_at"] = _now()
        self.runs.append(self._current)
        self._current = None

    # -- steps ----------------------------------------------------------
    def log_step(self, step_type, tool_name=None, content="",
                 latency_ms=0.0, tokens_in=0, tokens_out=0, error=None):
        assert self._current is not None, "start_run() must be called first"
        step = {
            "step_id": self._step_id,
            "type": step_type,  # reason | tool_call | observation | final
            "tool_name": tool_name,
            "content": content,
            "latency_ms": round(latency_ms, 3),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "error": error,
            "timestamp": _now(),
        }
        self._current["steps"].append(step)
        self._step_id += 1
        return step

    def reason(self, content, latency_ms=0.0):
        """Log a reasoning/planning step."""
        return self.log_step("reason", content=content,
                             latency_ms=latency_ms,
                             tokens_in=count_tokens(content))

    def final(self, content):
        """Log the agent's final answer."""
        return self.log_step("final", content=content,
                             tokens_out=count_tokens(content))

    def tool_call(self, tool_name, func, *args, **kwargs):
        """Execute func as a tool call, timing it with perf_counter.

        Logs a tool_call step (with the arguments) and an observation step
        (with the result). If func raises, the error is recorded on the
        tool_call step and the exception is re-raised so the agent can
        handle it explicitly.
        """
        arg_text = " ".join(
            [repr(a) for a in args] +
            [f"{k}={v!r}" for k, v in kwargs.items()]
        )
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            self.log_step(
                "tool_call", tool_name=tool_name, content=arg_text,
                latency_ms=latency_ms,
                tokens_in=count_tokens(arg_text),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        latency_ms = (time.perf_counter() - t0) * 1000
        result_text = str(result)
        self.log_step(
            "tool_call", tool_name=tool_name, content=arg_text,
            latency_ms=latency_ms,
            tokens_in=count_tokens(arg_text),
            tokens_out=count_tokens(result_text),
        )
        self.log_step(
            "observation", tool_name=tool_name, content=result_text,
            tokens_in=count_tokens(result_text),
        )
        return result

    # -- persistence ----------------------------------------------------
    def save_jsonl(self, path):
        with open(path, "w") as f:
            for run in self.runs:
                f.write(json.dumps(run) + "\n")


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
