"""Input Guardrail - validates every request before any work is done.

Checks relevance, safety, policy (India-only) and validity. Blocks with a reason and stops the workflow.
Rule-based by default (fast, free, works offline); uses the LLM as a second opinion when available.
"""

import re

from langchain_core.messages import SystemMessage

from travel_agent.config import DEMO_MODE
from travel_agent.state import GuardrailVerdict, TravelState

# Obvious unsafe / disallowed intents.
_UNSAFE = re.compile(
    r"\b(bomb|weapon|explosive|smuggl|traffborn|traffick|drug deal|launder|hack|kill|terror|"
    r"fake passport|forged|illegal border|evade customs)\b",
    re.I,
)
_TRAVEL_HINTS = re.compile(
    r"\b(trip|travel|visit|holiday|vacation|tour|itinerary|flight|train|hotel|stay|days?|nights?|"
    r"weekend|honeymoon|weather|budget|places?|things to do|go to|getaway|plan)\b",
    re.I,
)
SYSTEM = (
    "You are the input guardrail for an India travel planner. Decide if the user's message is a safe, "
    "relevant travel-planning request (or a follow-up to one). Block only clearly unsafe, abusive, or "
    "completely unrelated messages. A trip request to a foreign country is still 'ok' here (scope is "
    "enforced later). Set category to one of: ok, irrelevant, unsafe, invalid."
)


def _rule_check(query: str, is_followup: bool) -> GuardrailVerdict:
    q = (query or "").strip()
    if len(q) < 2:
        return GuardrailVerdict(allow=False, reason="Please describe your trip.", category="invalid")
    if _UNSAFE.search(q):
        return GuardrailVerdict(
            allow=False,
            reason="This request looks unsafe or against policy, so I can't help with it. "
            "I can plan safe, legal travel within India.",
            category="unsafe",
        )
    if is_followup or _TRAVEL_HINTS.search(q):
        return GuardrailVerdict(allow=True, category="ok")
    return GuardrailVerdict(
        allow=False,
        reason="I'm a travel planner for trips within India. Tell me where you'd like to go and for how long, "
        'e.g. "4 days in Goa from Bengaluru".',
        category="irrelevant",
    )


def guardrail_node(state: TravelState) -> dict:
    query = state["user_query"]
    is_followup = bool(state.get("trip"))
    verdict = _rule_check(query, is_followup)

    from travel_agent.responsible_ai import (
        detect_injection,
        effective_engine,
        is_model_engine,
        moderate_safety,
        rai_event,
        OutputGuardResult,
        SafetyVerdict,
    )

    llm_calls = 0
    engine = "rules"
    injection = detect_injection(query)  # cheap, runs even in demo
    if verdict.allow and injection.detected:
        verdict = GuardrailVerdict(
            allow=False, category="injection",
            reason="This message looks like a prompt-injection / jailbreak attempt, so I can't act on it. "
            "Please describe your trip normally.",
        )

    # Responsible-AI safety check (Llama Guard when available, else rules) on the user's input.
    safety = SafetyVerdict(True)
    if verdict.allow:
        safety = moderate_safety(query, role="user")
        engine = safety.engine
        if is_model_engine(engine):
            llm_calls += 1
        if not safety.safe:
            verdict = GuardrailVerdict(
                allow=False, category="unsafe",
                reason="This request was flagged as unsafe by the safety checker, so I can't help with it. "
                "I can plan safe, legal travel within India.",
            )

    # If still allowed, let the general LLM catch subtler irrelevant/unsafe cases (only when no guard model ran).
    if verdict.allow and not DEMO_MODE and not is_model_engine(engine):
        try:
            from travel_agent.llm import get_structured_llm

            llm_verdict: GuardrailVerdict = get_structured_llm(GuardrailVerdict).invoke(
                [SystemMessage(content=SYSTEM), ("human", query)]
            )
            llm_calls += 1
            if not llm_verdict.allow and llm_verdict.category in {"unsafe", "irrelevant"}:
                verdict = llm_verdict
        except Exception:
            pass

    event = rai_event("guardrail", "input", OutputGuardResult(
        text=query, pii=[], injection=injection.detected, safety=safety, scope_ok=None, disclaimer_added=False,
    ))
    event["engine"] = engine
    update = {
        "guardrail_passed": verdict.allow,
        "guardrail_reason": verdict.reason,
        "llm_calls": llm_calls,
        "rai_log": [event],
    }
    if not verdict.allow:
        update["final_response"] = f"🛑 **Request blocked by guardrail** ({verdict.category}).\n\n{verdict.reason}"
    return update
