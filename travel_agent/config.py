import os

import requests
from dotenv import load_dotenv

load_dotenv()


def _real(key: str) -> bool:
    return bool(key) and not key.startswith("your_")


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not _real(TAVILY_API_KEY):
    TAVILY_API_KEY = ""
if not _real(GROQ_API_KEY):
    GROQ_API_KEY = ""


def _ollama_running() -> bool:
    try:
        return requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2).ok
    except requests.RequestException:
        return False


def _pick_provider() -> str:
    """LLM_PROVIDER=auto|ollama|groq|demo. Auto prefers Groq (if a key is set), then local Ollama, then demo."""
    choice = os.getenv("LLM_PROVIDER", "auto").lower()
    if os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"}:
        return "demo"
    if choice in {"groq", "ollama", "demo"}:
        return choice
    if GROQ_API_KEY:
        return "groq"
    if _ollama_running():
        return "ollama"
    return "demo"


LLM_PROVIDER = _pick_provider()
# Demo mode runs the full workflow with built-in sample data and no LLM.
DEMO_MODE = LLM_PROVIDER == "demo"

# Travel scope: "global" (any country, default) or "india" (India-only policy).
TRAVEL_SCOPE = os.getenv("TRAVEL_SCOPE", "global").lower()

# Evaluation: include the LLM-as-judge score (1 extra model call) in the per-run evaluation.
ENABLE_LLM_JUDGE = os.getenv("ENABLE_LLM_JUDGE", "true").lower() in {"1", "true", "yes"}

# ---- Responsible AI ----
ENABLE_RAI = os.getenv("ENABLE_RAI", "true").lower() in {"1", "true", "yes"}
SAFETY_ENGINE = os.getenv("SAFETY_ENGINE", "auto").lower()  # auto | llama_guard | rules
GUARD_GROQ_MODEL = os.getenv("GUARD_GROQ_MODEL", "meta-llama/llama-guard-4-12b")
GUARD_OLLAMA_MODEL = os.getenv("GUARD_OLLAMA_MODEL", "llama-guard3")
MODEL_LABEL = {
    "groq": f"Groq free tier - {GROQ_MODEL}",
    "ollama": f"Ollama (local, free) - {OLLAMA_MODEL}",
    "demo": "Demo mode (no LLM)",
}[LLM_PROVIDER]

# langchain-tavily reads the key from the environment
if TAVILY_API_KEY:
    os.environ.setdefault("TAVILY_API_KEY", TAVILY_API_KEY)
