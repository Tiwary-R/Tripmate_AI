"""Agent evaluation - scores the quality of a completed plan.

Combines fast, deterministic heuristic metrics (no model call) with an optional LLM-as-judge score
(relevance / coherence / helpfulness). Returns an `eval_report` dict the UI renders as a score + breakdown.
Free/local: the judge reuses the project's own Ollama/Groq model via get_structured_llm.
"""

import re

from pydantic import BaseModel, Field

from travel_agent.config import DEMO_MODE, ENABLE_LLM_JUDGE
from travel_agent.state import SPECIALIST_AGENTS

# Map each specialist to its output key and the heading the final plan should contain when it ran.
_AGENT_OUTPUT = {
    "flight_agent": ("flight_results", ("flight", "train", "transport")),
    "hotel_agent": ("hotel_results", ("hotel", "stay", "where to stay")),
    "weather_agent": ("weather_info", ("weather", "packing")),
    "budget_agent": ("budget_analysis", ("budget", "cost", "estimate")),
    "itinerary_agent": ("itinerary", ("itinerary", "day")),
}
_CURRENCY = re.compile(r"(₹|rs\.?|inr|\$|usd|€|eur|£|gbp|¥|jpy|aed|dirham|rupee|dollar|euro|yen|baht|฿)", re.I)
# Heuristic weights (+ judge). Normalised at combination time.
_WEIGHTS = {"completeness": 0.30, "safety": 0.25, "grounding": 0.20, "personalization": 0.10,
            "efficiency": 0.15, "judge": 0.40}


class JudgeScore(BaseModel):
    """LLM-as-judge rubric (each 0-10)."""

    relevance: int = Field(..., ge=0, le=10, description="Does the plan match the request (destination, days, interests, budget)?")
    coherence: int = Field(..., ge=0, le=10, description="Is it well-structured, consistent and easy to follow?")
    helpfulness: int = Field(..., ge=0, le=10, description="Is it practical and genuinely useful for the traveller?")
    rationale: str = Field("", description="One short sentence explaining the scores.")


def _pct(part: float, whole: float) -> int:
    return int(round(100 * part / whole)) if whole else 100


def _completeness(state: dict) -> tuple[int, str]:
    selected = [a for a in SPECIALIST_AGENTS if a in (state.get("selected_agents") or [])]
    final = state.get("final_response") or ""
    if not selected:
        return (100 if final else 0), "no specialists selected"
    produced = sum(1 for a in selected if (state.get(_AGENT_OUTPUT[a][0]) or "").strip())
    checks = produced + (1 if final.strip() else 0)
    total = len(selected) + 1
    return _pct(checks, total), f"{produced}/{len(selected)} agents produced output; final plan {'present' if final else 'missing'}"


def _safety(state: dict) -> tuple[int, str]:
    if not state.get("guardrail_passed", True):
        return 0, "blocked by guardrail"
    events = state.get("rai_log") or []
    unsafe = sum(1 for e in events if not e.get("safety", {}).get("safe", True))
    leaks = sum(len(e.get("pii") or []) for e in events)
    inj = sum(1 for e in events if e.get("injection"))
    score = 100 - unsafe * 50 - leaks * 15 - inj * 20
    detail = "clean" if (unsafe or leaks or inj) == 0 else f"unsafe={unsafe}, pii={leaks}, injection={inj}"
    return max(score, 0), detail


def _grounding(state: dict) -> tuple[int, str]:
    final = state.get("final_response") or ""
    if not final:
        return 0, "no final plan"
    selected = state.get("selected_agents") or []
    checks, passed, notes = 0, 0, []
    # currency present somewhere in the plan (budget/flight/hotel reports feed into it)
    if any(a in selected for a in ("budget_agent", "flight_agent", "hotel_agent")):
        checks += 1
        if _CURRENCY.search(final):
            passed += 1
        else:
            notes.append("no currency shown")
    # itinerary day coverage
    if "itinerary_agent" in selected:
        checks += 1
        days = (state.get("trip") or {}).get("num_days") or 0
        day_headings = len(re.findall(r"(?im)^\s*#*\s*day\s*\d+|day\s*\d+\s*[:\-]", state.get("itinerary") or ""))
        if days and day_headings >= days:
            passed += 1
        else:
            notes.append(f"itinerary days {day_headings}/{days}")
    # weather present if it ran
    if "weather_agent" in selected:
        checks += 1
        if (state.get("weather_info") or "").strip():
            passed += 1
        else:
            notes.append("weather missing")
    return (_pct(passed, checks) if checks else 100), ("; ".join(notes) or "grounded")


def _personalization(state: dict) -> tuple[int, str]:
    final = (state.get("final_response") or "").lower()
    signals = list(state.get("preferences") or [])
    recalled = state.get("recalled_memory") or ""
    if not signals and not recalled:
        return 100, "no saved preferences/memory to apply (N/A)"
    hits = sum(1 for p in signals if p and any(w in final for w in str(p).lower().split() if len(w) > 3))
    applied = hits + (1 if recalled and any(w in final for w in recalled.lower().split() if len(w) > 4) else 0)
    whole = len(signals) + (1 if recalled else 0)
    return _pct(applied, whole), f"{applied}/{whole} personalization signals reflected"


def _efficiency(state: dict, latency_s: float | None) -> tuple[int, str]:
    calls = state.get("llm_calls") or 0
    score = 100
    if calls > 8:
        score -= min((calls - 8) * 5, 40)
    detail = f"{calls} LLM calls"
    if latency_s is not None:
        if latency_s > 180:
            score -= 30
        elif latency_s > 90:
            score -= 15
        detail += f", {latency_s:.0f}s"
    return max(score, 0), detail


def _judge(state: dict) -> JudgeScore | None:
    if DEMO_MODE or not ENABLE_LLM_JUDGE:
        return None
    from travel_agent.agents.common import trip_summary
    from travel_agent.llm import get_structured_llm

    system = (
        "You are a strict travel-plan evaluator. Score the plan for the given request on three rubrics "
        "(0-10 each): relevance, coherence, helpfulness. Be fair but critical. Give a one-sentence rationale."
    )
    user = f"Request context:\n{trip_summary(state)}\n\nThe plan:\n{(state.get('final_response') or '')[:4000]}"
    try:
        return get_structured_llm(JudgeScore).invoke([("system", system), ("human", user)])
    except Exception:
        return None


def _grade(score: int) -> str:
    return next(g for t, g in [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")] if score >= t)


def evaluate(state: dict, latency_s: float | None = None, use_judge: bool = True) -> dict:
    """Score a completed plan. Returns the eval_report dict (see module docstring)."""
    metrics = {
        "completeness": _completeness(state),
        "safety": _safety(state),
        "grounding": _grounding(state),
        "personalization": _personalization(state),
        "efficiency": _efficiency(state, latency_s),
    }
    judge = _judge(state) if use_judge else None
    judge_pct = None
    if judge is not None:
        judge_pct = int(round(100 * (judge.relevance + judge.coherence + judge.helpfulness) / 30))

    active = {k: v[0] for k, v in metrics.items()}
    if judge_pct is not None:
        active["judge"] = judge_pct
    total_w = sum(_WEIGHTS[k] for k in active)
    overall = int(round(sum(active[k] * _WEIGHTS[k] for k in active) / total_w)) if total_w else 0

    notes = [f"{k}: {v[1]}" for k, v in metrics.items() if v[0] < 100]
    return {
        "overall": overall,
        "grade": _grade(overall),
        "metrics": [{"name": k.capitalize(), "score": v[0], "detail": v[1]} for k, v in metrics.items()]
        + ([{"name": "LLM judge", "score": judge_pct, "detail": judge.rationale}] if judge is not None else []),
        "judge": judge.model_dump() if judge is not None else None,
        "notes": notes,
        "llm_judged": judge is not None,
    }
