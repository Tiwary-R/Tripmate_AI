"""Responsible AI primitives: safety moderation, PII redaction, prompt-injection defense, transparency.

Design:
- Per-agent output guard (`fast_output_guard`) is regex-only - zero model calls, safe for parallel agents.
- Heavier Llama Guard moderation (`moderate_safety`) runs only at the two ends (input + final output).
- Llama Guard (free) is auto-detected (Groq free tier model, or local Ollama 'llama-guard3'); if neither is
  available it degrades to rule-based scanning. Everything stays free and never hard-fails.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

import requests

from travel_agent.config import (
    DEMO_MODE,
    ENABLE_RAI,
    GUARD_GROQ_MODEL,
    GUARD_OLLAMA_MODEL,
    GROQ_API_KEY,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    SAFETY_ENGINE,
)
from travel_agent.india import is_indian_place

DISCLAIMER = "_Prices, schedules and availability are estimates — please confirm at the time of booking._"
FAIRNESS_NOTE = (
    " Be inclusive and non-discriminatory: suggest options suitable for travellers of any gender, religion, "
    "ability, caste or background, and respect accessibility needs."
)

# --------------------------------------------------------------------------------------------------
# Verdict / result types
# --------------------------------------------------------------------------------------------------


@dataclass
class SafetyVerdict:
    safe: bool
    categories: list[str] = field(default_factory=list)
    engine: str = "rules"  # llama_guard_groq | llama_guard_ollama | rules
    reason: str = ""


@dataclass
class PIIResult:
    text: str
    found: list[str] = field(default_factory=list)


@dataclass
class InjectionResult:
    detected: bool
    patterns: list[str] = field(default_factory=list)


@dataclass
class OutputGuardResult:
    text: str
    pii: list[str] = field(default_factory=list)
    injection: bool = False
    safety: SafetyVerdict = field(default_factory=lambda: SafetyVerdict(True))
    scope_ok: bool | None = None
    disclaimer_added: bool = False


# --------------------------------------------------------------------------------------------------
# PII redaction
# --------------------------------------------------------------------------------------------------

# Order matters: longer digit groups (aadhaar/card) before the 10-digit phone rule.
_PII = [
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("aadhaar", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
    ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?91[\-\s]?|0)?[6-9]\d{4}[\s\-]?\d{5}(?!\d)")),
]


def redact_pii(text: str) -> PIIResult:
    if not text:
        return PIIResult(text=text or "", found=[])
    found: list[str] = []
    out = text
    for kind, pattern in _PII:
        if pattern.search(out):
            found.append(kind)
            out = pattern.sub(f"[REDACTED_{kind.upper()}]", out)
    return PIIResult(text=out, found=found)


# --------------------------------------------------------------------------------------------------
# Prompt-injection detection
# --------------------------------------------------------------------------------------------------

_INJECTION = [
    re.compile(r"ignore\s+(all\s+|the\s+)?(previous|above|prior|earlier)?\s*(instructions|prompts?|rules)", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|above|previous|all)", re.I),
    re.compile(r"\b(you are now|act as|pretend to be|jailbreak|developer mode|do anything now|dan mode)\b", re.I),
    re.compile(r"(reveal|show|print|repeat)\s+(your\s+)?(system\s+)?(prompt|instructions)", re.I),
    re.compile(r"</?(system|assistant|user)>", re.I),
]


def detect_injection(text: str) -> InjectionResult:
    hits = [p.pattern for p in _INJECTION if p.search(text or "")]
    return InjectionResult(detected=bool(hits), patterns=hits)


# --------------------------------------------------------------------------------------------------
# Safety moderation (Llama Guard with graceful fallback to rules)
# --------------------------------------------------------------------------------------------------

_UNSAFE_KEYWORDS = re.compile(
    r"\b(bomb|weapon|explosive|smuggl|traffick|drug deal|launder|hack|kill|terror|"
    r"fake passport|forged|illegal border|evade customs|suicide|self[- ]harm|child abuse)\b",
    re.I,
)
_MODEL_ENGINES = {"llama_guard_groq", "llama_guard_ollama"}


def is_model_engine(engine: str) -> bool:
    return engine in _MODEL_ENGINES


@lru_cache
def _ollama_has_guard() -> bool:
    try:
        tags = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3).json().get("models", [])
        return any(GUARD_OLLAMA_MODEL.split(":")[0] in m.get("name", "") for m in tags)
    except Exception:
        return False


@lru_cache
def effective_engine() -> str:
    """Resolve which safety engine to use, once. Returns 'llama_guard_groq' | 'llama_guard_ollama' | 'rules'."""
    if not ENABLE_RAI or DEMO_MODE or SAFETY_ENGINE == "rules":
        return "rules"
    if SAFETY_ENGINE in {"auto", "llama_guard"}:
        if LLM_PROVIDER == "groq" and GROQ_API_KEY:
            return "llama_guard_groq"
        if _ollama_has_guard():
            return "llama_guard_ollama"
    return "rules"


def safety_engine_label() -> str:
    return {
        "llama_guard_groq": f"Llama Guard (Groq · {GUARD_GROQ_MODEL})",
        "llama_guard_ollama": f"Llama Guard (Ollama · {GUARD_OLLAMA_MODEL})",
        "rules": "Rule-based scan" + ("" if DEMO_MODE else " (pull llama-guard3 or add a Groq key for Llama Guard)"),
    }[effective_engine()]


@lru_cache
def _guard_llm():
    engine = effective_engine()
    if engine == "llama_guard_groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=GUARD_GROQ_MODEL, temperature=0, api_key=GROQ_API_KEY)
    if engine == "llama_guard_ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=GUARD_OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    return None


def _parse_guard(out: str, engine: str) -> SafetyVerdict:
    lines = (out or "").strip().splitlines()
    first = lines[0].strip().lower() if lines else ""
    if not first or first.startswith("safe"):
        return SafetyVerdict(safe=True, engine=engine)
    cats = re.findall(r"S\d+", out or "")
    if "unsafe" in first or cats:
        return SafetyVerdict(safe=False, categories=cats, engine=engine,
                             reason="flagged categories: " + (", ".join(cats) or "unspecified"))
    return SafetyVerdict(safe=True, engine=engine)  # unexpected prose -> don't false-block benign text


def _rules_safety(text: str) -> SafetyVerdict:
    if _UNSAFE_KEYWORDS.search(text or ""):
        return SafetyVerdict(safe=False, categories=["keyword"], engine="rules",
                             reason="matched an unsafe keyword")
    return SafetyVerdict(safe=True, engine="rules")


def moderate_safety(text: str, role: str = "user") -> SafetyVerdict:
    """Classify text as safe/unsafe. Uses Llama Guard when available, else a rule-based scan."""
    rules = _rules_safety(text)
    if not rules.safe:  # rules are a hard floor - always block obvious terms
        return rules
    llm = _guard_llm()
    if llm is None:
        return rules
    try:
        from langchain_core.messages import AIMessage, HumanMessage

        convo = [HumanMessage(content="Plan a trip."), AIMessage(content=text)] if role == "assistant" \
            else [HumanMessage(content=text)]
        resp = llm.invoke(convo)
        return _parse_guard(resp.content, effective_engine())
    except Exception:
        return rules  # never hard-fail on a guard error


# --------------------------------------------------------------------------------------------------
# Output guard applied to every agent (regex-only, no model calls)
# --------------------------------------------------------------------------------------------------


def fast_output_guard(text: str, disclaimer: str | None = None, place: str | None = None) -> OutputGuardResult:
    pii = redact_pii(text)
    inj = detect_injection(pii.text)  # defensive: a tool/web result may have carried an injection
    safety = _rules_safety(pii.text)
    out = pii.text
    added = False
    if disclaimer and disclaimer not in out:
        out = f"{out}\n\n{disclaimer}"
        added = True
    return OutputGuardResult(
        text=out, pii=pii.found, injection=inj.detected, safety=safety,
        scope_ok=is_indian_place(place), disclaimer_added=added,
    )


# --------------------------------------------------------------------------------------------------
# Transparency event + per-agent wrapper
# --------------------------------------------------------------------------------------------------

AGENT_OUTPUT_KEY = {
    "flight_agent": "flight_results",
    "hotel_agent": "hotel_results",
    "weather_agent": "weather_info",
    "budget_agent": "budget_analysis",
    "itinerary_agent": "itinerary",
    "final_agent": "final_response",
}
_PRICE_AGENTS = {"flight_agent", "hotel_agent", "budget_agent"}


def rai_event(node: str, stage: str, res: OutputGuardResult) -> dict:
    return {
        "node": node,
        "stage": stage,
        "pii": res.pii,
        "injection": res.injection,
        "safety": {"safe": res.safety.safe, "engine": res.safety.engine, "categories": res.safety.categories},
        "scope_ok": res.scope_ok,
        "disclaimer": res.disclaimer_added,
    }


def with_output_guardrail(fn, name: str):
    """Wrap an agent node so its output is PII-redacted, safety-scanned and disclaimer-tagged.

    final_agent additionally gets a Llama Guard pass and keeps its AIMessage in sync.
    """
    key = AGENT_OUTPUT_KEY[name]

    def wrapped(state, *args, **kwargs):
        update = fn(state, *args, **kwargs) or {}
        if not ENABLE_RAI or not isinstance(update.get(key), str) or not update[key]:
            return update

        place = (state.get("trip") or {}).get("destination")
        # A real multi-agent plan ran only if the supervisor selected agents (not a block/clarification).
        is_real_plan = bool(state.get("selected_agents"))
        disclaimer = DISCLAIMER if (name in _PRICE_AGENTS or (name == "final_agent" and is_real_plan)) else None
        res = fast_output_guard(update[key], disclaimer=disclaimer, place=place)

        if name == "final_agent" and is_real_plan and not DEMO_MODE:
            verdict = moderate_safety(res.text, role="assistant")
            res.safety = verdict
            if is_model_engine(verdict.engine):
                update["llm_calls"] = update.get("llm_calls", 0) + 1
            if not verdict.safe:
                res.text = ("⚠️ I couldn't share this plan because it was flagged by the safety checker. "
                            "Please try rephrasing your request.")

        update[key] = res.text
        if name == "final_agent" and update.get("messages"):
            from langchain_core.messages import AIMessage

            update["messages"] = [AIMessage(content=res.text)]

        update["rai_log"] = [rai_event(name, "final" if name == "final_agent" else "output", res)]
        return update

    wrapped.__name__ = f"guarded_{name}"
    return wrapped
