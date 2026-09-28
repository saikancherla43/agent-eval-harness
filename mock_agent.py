"""Deterministic mock agent with scripted tools.

This is a *stand-in* for a real LLM agent: its policy is rule-based and
fully deterministic, so eval numbers are reproducible run to run. In a
client engagement this module is replaced by the client's real agent —
the harness only requires a callable with the signature
``agent_fn(scenario, tracer) -> str``.

The mock deliberately contains one naive heuristic (see
``_extract_price_answer``): it ignores billing-period qualifiers like
"per year", so the "Pro plan per year" scenario fails. The harness exists
to catch exactly this kind of silent agent bug.
"""

import re
import time


# -- scripted tools ------------------------------------------------------

DOCS = {
    "pricing": (
        "Acme Cloud pricing: Starter $0/mo (100 build minutes), "
        "Growth $29/seat/mo (1,000 build minutes), "
        "Pro $79/seat/mo (5,000 build minutes) billed monthly, "
        "or $790/seat/yr billed annually."
    ),
    "sla": (
        "Acme Cloud uptime SLA: 99.9% monthly uptime. "
        "Service credits apply if uptime falls below 99.9% in a calendar month."
    ),
    "refund": (
        "Annual plans: full refund within 30 days of purchase, prorated after. "
        "Monthly plans are non-refundable."
    ),
}


def search_docs(query):
    """Keyword search over the mini help-center. Simulated 50 ms latency."""
    time.sleep(0.05)
    q = query.lower()
    if "refund" in q or "cancel" in q:
        return DOCS["refund"]
    if "sla" in q or "uptime" in q:
        return DOCS["sla"]
    if any(k in q for k in ("price", "pricing", "cost", "plan")):
        return DOCS["pricing"]
    return "No matching docs found."


WEATHER = {
    "berlin": "18C, partly cloudy",
    "paris": "21C, sunny",
    "tokyo": "24C, light rain",
}


def get_weather(city):
    """Scripted weather lookup. Simulated 80 ms latency. Raises for unknown cities."""
    time.sleep(0.08)
    key = city.strip().lower()
    if key not in WEATHER:
        raise ValueError(f"no weather data for {city!r}")
    return WEATHER[key]


def calculator(expression):
    """Sandboxed arithmetic. Only digits and operators are accepted."""
    time.sleep(0.01)
    if not re.fullmatch(r"[\d\s.\+\-\*\/\(\)%]+", expression):
        raise ValueError(f"refusing to evaluate {expression!r}")
    return str(eval(expression, {"__builtins__": {}}, {}))  # arithmetic only


# -- deterministic policy --------------------------------------------------

def _extract_city(question):
    m = re.search(r"weather\s+(?:in|for)\s+([A-Za-z][A-Za-z ]*?)\s*\??$",
                  question.strip(), re.I)
    return m.group(1).strip() if m else None


def _extract_expression(question):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", question, re.I)
    if m:
        return f"({m.group(1)}/100)*{m.group(2)}", f"{m.group(1)}% of {m.group(2)}"
    m = re.search(r"(\d+(?:\.\d+)?)\s+divided by\s+(\d+(?:\.\d+)?)", question, re.I)
    if m:
        return f"{m.group(1)}/{m.group(2)}", f"{m.group(1)} divided by {m.group(2)}"
    return None


def _extract_price_answer(question, doc):
    """Naive price extraction: find the plan keyword, return the monthly
    price printed right after it.

    INTENTIONAL BUG (documented): the billing-period qualifier is ignored,
    so "How much does the Pro plan cost per year?" returns the *monthly*
    price. A real agent misreading qualifiers fails the same way — and the
    eval harness catches it.
    """
    m = re.search(r"\b(starter|growth|pro)\b", question, re.I)
    if not m:
        return None
    plan = m.group(1).lower()
    pm = re.search(plan + r"\s+(\$[\d,]+(?:\.\d+)?/seat/mo)", doc, re.I)
    if pm:
        return f"The {plan.title()} plan costs {pm.group(1)}."
    return None


def mock_agent(scenario, tracer):
    """Run one scenario. Returns the final answer string."""
    question = scenario["question"]

    t0 = time.perf_counter()
    city = _extract_city(question)
    expr = _extract_expression(question)
    if city:
        route = ("weather", f"weather question about {city}; call get_weather")
    elif expr:
        route = ("math", f"arithmetic '{expr[1]}'; call calculator")
    else:
        route = ("docs", "knowledge question; call search_docs")
    reason_ms = (time.perf_counter() - t0) * 1000
    tracer.reason(f"Plan: {route[1]}", latency_ms=reason_ms)

    if route[0] == "weather":
        try:
            obs = tracer.tool_call("get_weather", get_weather, city)
            answer = f"The weather in {city} is {obs}."
        except Exception as exc:
            tracer.log_step(
                "observation", tool_name="get_weather",
                content=f"Tool error: {exc}",
                error=f"{type(exc).__name__}: {exc}",
            )
            answer = f"Sorry, I couldn't get the weather for {city}."
    elif route[0] == "math":
        code, label = expr
        result = tracer.tool_call("calculator", calculator, code)
        answer = f"{label} = {result}."
    else:
        doc = tracer.tool_call("search_docs", search_docs, question)
        price_answer = _extract_price_answer(question, doc)
        if price_answer:
            answer = price_answer
        else:
            answer = doc.split(". ")[0].rstrip(".") + "."

    tracer.final(answer)
    return answer
