# TripMate AI — Multi-Agent Travel Planner

Turn a plain-English request (e.g. *"5 days in Paris from Mumbai, mid-range, museums and food"*) into a
complete travel plan — flights/transport, hotels, weather, a day-by-day itinerary and a budget — produced by
a team of AI agents, **orchestrated on Google ADK**, with Responsible-AI guardrails and an automated quality
score. **Worldwide** by default. **Free and local** (local Llama via Ollama + free APIs; no paid services).

## Highlights
- **Multi-agent workflow (Google ADK):** Input Guardrail → Supervisor (dynamic routing) → optional Human
  Review → Flight / Hotel / Weather / Budget / Itinerary (in parallel) → Final Response → Evaluation.
- **Worldwide** trips (set `TRAVEL_SCOPE=india` for India-only).
- **Free LLM:** Ollama `llama3.2` by default, or the free **Groq** tier (Llama 3.3 70B) for higher quality.
- **MCP tools:** weather (Open-Meteo, free/no key), flights (AviationStack), search/places (Tavily, Google).
- **Responsible AI** on every agent: PII redaction, safety moderation (Llama Guard + rules),
  prompt-injection defense, grounding disclaimers, and a transparency panel.
- **Memory:** durable ADK sessions (SQLite), long-term trip recall, and per-user preferences.
- **Evaluation:** heuristic metrics + optional LLM-as-judge, shown as a score in the UI, plus an offline suite.

## Quick start
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env            # optional: add free keys / settings
.venv\Scripts\python -m streamlit run streamlit_app.py
# open http://localhost:8502  (log in or register, then describe a trip)
```
Requires a local [Ollama](https://ollama.com) with `ollama pull llama3.2`, **or** a free `GROQ_API_KEY`.

## Interfaces
- **Streamlit web app** (primary): `streamlit run streamlit_app.py`
- **CLI:** `python cli.py --user you`
- **Offline evaluation:** `python evaluate_suite.py` (add `--live` to use the LLM)

## Configuration (`.env`, all optional)
| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | `auto` / `ollama` / `groq` / `demo` | `auto` |
| `OLLAMA_MODEL` | local model | `llama3.2` |
| `GROQ_API_KEY` / `GROQ_MODEL` | free cloud LLM (better quality) | — / `llama-3.3-70b-versatile` |
| `TRAVEL_SCOPE` | `global` or `india` | `global` |
| `ENABLE_RAI` | Responsible-AI guardrails | `true` |
| `SAFETY_ENGINE` | `auto` / `llama_guard` / `rules` | `auto` |
| `ENABLE_LLM_JUDGE` | include LLM judge in the score | `true` |
| `USE_MCP` | call tools via MCP servers | `true` |
| `ADK_SQLITE_SESSIONS` | session DB URL (durable) | auto SQLite |
| `TAVILY_API_KEY`, `AVIATIONSTACK_API_KEY`, `GOOGLE_MAPS_API_KEY` | optional live data | — |

## Project layout
```
streamlit_app.py            Web UI (login, progress, result tabs, RAI + Evaluation panels)
cli.py                      Terminal chat
evaluate_suite.py           Offline evaluation suite
scripts/md2pdf.py           Markdown -> PDF converter for the docs
travel_agent/
  orchestrator.py           ADK-based TravelPlanner (sessions, state, memory, routing)
  state.py                  TravelState + Pydantic models
  config.py                 Settings / provider resolution
  llm.py                    LLM factory (Ollama / Groq)
  memory.py                 ADK session service + SQLite PreferenceStore / MemoryStore
  evaluation.py             Heuristic + LLM-judge scoring
  responsible_ai.py         PII/safety/injection guards + per-agent wrapper
  india.py                  Scope policy + worldwide airport resolution
  demo.py                   Offline sample data (no-LLM mode)
  agents/                   guardrail, supervisor, human_review, 5 specialists, final
  tools/                    weather (Open-Meteo), flights, search, places
mcp_servers/                Runnable MCP servers (weather, flights, search)
tests/                      pytest suite
docs: DOCUMENTATION.md, AGENTS_AND_ADK.md, PROJECT_OVERVIEW.md, AWS_ARCHITECTURE.md, LOCAL_VS_AWS_COMPARISON.md
```

## Notes
- Orchestration is **Google ADK** (LangGraph was removed from the app code).
- Without optional data keys, tools degrade gracefully (sample/searched data) and the plan is still produced.
- Everything persists locally in SQLite (`preferences.db`, `memory.db`, `adk_sessions.db`, `scores.db`,
  `users.db`) — all git-ignored.
