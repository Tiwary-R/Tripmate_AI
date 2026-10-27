"""ADK-based orchestrator - replaces the LangGraph graph.

Google ADK provides the runtime: an `SessionService` holds per-conversation state and an append-only event
log; each workflow step persists its update as an ADK `Event` with a `state_delta`. The control flow
(Guardrail -> Supervisor -> Human review -> dynamically-selected specialists -> Final) is driven here, which
reproduces the previous routing and the exact `TravelPlanner` interface the UI/CLI depend on.

Free & local: the LLM still runs through travel_agent/llm.py (Ollama by default). ADK adds no paid calls.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.events import Event, EventActions

from travel_agent.agents.budget_agent import budget_agent
from travel_agent.agents.final_agent import final_agent
from travel_agent.agents.flight_agent import flight_agent
from travel_agent.agents.guardrail import guardrail_node
from travel_agent.agents.hotel_agent import hotel_agent
from travel_agent.agents.human_review import apply_decision, review_payload
from travel_agent.agents.itinerary_agent import itinerary_agent
from travel_agent.agents.supervisor import supervisor_node
from travel_agent.agents.weather_agent import weather_agent
from travel_agent.memory import MemoryStore, PreferenceStore, ScoreLog, make_session_service
from travel_agent.responsible_ai import with_output_guardrail
from travel_agent.state import SPECIALIST_AGENTS

APP_NAME = "tripmate"

# Specialists + final are wrapped with the Responsible-AI output guard (PII redaction, safety, disclaimer).
_SPECIALIST_FNS = {
    "flight_agent": with_output_guardrail(flight_agent, "flight_agent"),
    "hotel_agent": with_output_guardrail(hotel_agent, "hotel_agent"),
    "weather_agent": with_output_guardrail(weather_agent, "weather_agent"),
    "budget_agent": with_output_guardrail(budget_agent, "budget_agent"),
    "itinerary_agent": with_output_guardrail(itinerary_agent, "itinerary_agent"),
}
_FINAL_FN = with_output_guardrail(final_agent, "final_agent")

_TRANSIENT_RESET = {
    "guardrail_passed": False, "guardrail_reason": "", "selected_agents": [], "supervisor_reasoning": "",
    "hitl_feedback": "", "final_response": "", "flight_results": "", "hotel_results": "",
    "weather_info": "", "budget_analysis": "", "itinerary": "", "eval_report": {}, "_paused": False,
}


class _Loop:
    """A background asyncio loop so this sync code can drive ADK's async SessionService cleanly."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True, name="adk-loop").start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()


def _normalize_messages(msgs) -> list[dict]:
    out = []
    for m in msgs or []:
        if isinstance(m, dict):
            out.append(m)
        else:
            role = "user" if getattr(m, "type", None) == "human" else "assistant"
            out.append({"role": role, "content": getattr(m, "content", "")})
    return out


class _GraphShim:
    """Back-compat for cli.py which calls planner.graph.get_state({...}).values."""

    def __init__(self, planner):
        self._p = planner

    def get_state(self, config):
        thread = config["configurable"]["thread_id"]

        class _Snap:
            pass

        snap = _Snap()
        snap.values = self._p.get_values(thread)
        return snap


class TravelPlanner:
    """ADK-backed planner with the same public interface as the old LangGraph one."""

    def __init__(self):
        self.store = PreferenceStore()
        self.memory_store = MemoryStore()  # durable long-term trip memory
        self.score_log = ScoreLog()  # durable evaluation-score history
        self._svc, self.backend = make_session_service()
        try:
            from google.adk.memory import InMemoryMemoryService

            self._mem = InMemoryMemoryService()  # ADK memory API (runtime session recall)
        except Exception:
            self._mem = None
        self._loop = _Loop()
        self._thread_user: dict[str, str] = {}
        self.graph = _GraphShim(self)

    # ----- ADK session helpers -----
    def _ensure_session(self, thread: str, user: str):
        self._thread_user[thread] = user
        self.store.put(("thread_user",), thread, {"user": user})  # persist so reopened threads resolve after restart
        sess = self._loop.run(self._svc.get_session(app_name=APP_NAME, user_id=user, session_id=thread))
        if sess is None:
            self._loop.run(self._svc.create_session(app_name=APP_NAME, user_id=user, session_id=thread, state={}))

    def _resolve_user(self, thread: str) -> str:
        if thread in self._thread_user:
            return self._thread_user[thread]
        item = self.store.get(("thread_user",), thread)
        return item.value.get("user", "default") if item else "default"

    def _state(self, thread: str, user: str | None = None) -> dict:
        user = user or self._resolve_user(thread)
        sess = self._loop.run(self._svc.get_session(app_name=APP_NAME, user_id=user, session_id=thread))
        return dict(sess.state) if sess else {}

    def _apply(self, state: dict, update: dict) -> dict:
        """Apply reducers (sum llm_calls, concat rai_log, append messages, overwrite the rest). Returns delta."""
        delta = {}
        for k, v in update.items():
            if k == "llm_calls":
                nv = state.get("llm_calls", 0) + (v or 0)
            elif k == "rai_log":
                nv = state.get("rai_log", []) + list(v or [])
            elif k == "messages":
                nv = state.get("messages", []) + _normalize_messages(v)
            else:
                nv = v
            state[k] = nv
            delta[k] = nv
        return delta

    def _commit(self, thread: str, user: str, state: dict, update: dict) -> None:
        delta = self._apply(state, update)
        sess = self._loop.run(self._svc.get_session(app_name=APP_NAME, user_id=user, session_id=thread))
        self._loop.run(self._svc.append_event(sess, Event(author="tripmate", actions=EventActions(state_delta=delta))))

    # ----- config -----
    def _config(self, thread_id: str, user_id: str, hitl: bool = True) -> dict:
        return {"configurable": {"thread_id": thread_id, "user_id": user_id, "hitl": hitl}}

    # ----- public API -----
    def plan(self, query: str, thread_id: str, user_id: str = "default", hitl: bool = False) -> dict:
        for _ in self.stream(query, thread_id, user_id, hitl):
            pass
        return self.get_values(thread_id)

    def stream(self, query: str, thread_id: str, user_id: str = "default", hitl: bool = True):
        self._ensure_session(thread_id, user_id)
        state = self._state(thread_id, user_id)
        recalled = "; ".join(self.memory_store.recent(user_id))  # long-term memory of past trips
        self._commit(thread_id, user_id, state,
                     {**_TRANSIENT_RESET, "user_query": query, "user_id": user_id,
                      "recalled_memory": recalled, "_started_at": time.time()})

        # Guardrail
        upd = guardrail_node(state)
        self._commit(thread_id, user_id, state, upd)
        yield "guardrail", upd
        if not state.get("guardrail_passed"):
            yield from self._finalize(thread_id, user_id, state)
            return

        # Supervisor
        upd = supervisor_node(state, store=self.store, user_id=user_id)
        self._commit(thread_id, user_id, state, upd)
        yield "supervisor", upd
        if state.get("final_response"):  # clarification or policy block
            yield from self._finalize(thread_id, user_id, state)
            return

        # Human-in-the-loop
        if hitl:
            self._commit(thread_id, user_id, state, {"_paused": True})
            yield "__interrupt__", review_payload(state)
            return

        yield from self._specialists_and_final(thread_id, user_id, state)

    def resume(self, decision: dict, thread_id: str, user_id: str = "default", hitl: bool = True):
        self._thread_user[thread_id] = user_id
        state = self._state(thread_id, user_id)
        self._commit(thread_id, user_id, state, {"_paused": False})
        upd = apply_decision(decision)
        if upd:
            self._commit(thread_id, user_id, state, upd)
        if state.get("final_response"):  # cancelled
            yield from self._finalize(thread_id, user_id, state)
            return
        yield from self._specialists_and_final(thread_id, user_id, state)

    # ----- internal phases -----
    def _finalize(self, thread: str, user: str, state: dict):
        upd = _FINAL_FN(state)
        self._commit(thread, user, state, upd)
        yield "final_agent", upd

    def _specialists_and_final(self, thread: str, user: str, state: dict):
        selected = [a for a in SPECIALIST_AGENTS if a in (state.get("selected_agents") or [])]
        if selected:
            snapshot = dict(state)
            with ThreadPoolExecutor(max_workers=len(selected)) as pool:
                futures = {pool.submit(_SPECIALIST_FNS[name], dict(snapshot)): name for name in selected}
                for fut in as_completed(futures):
                    name = futures[fut]
                    upd = fut.result()
                    self._commit(thread, user, state, upd)
                    yield name, upd
        yield from self._finalize(thread, user, state)
        yield from self._evaluate(thread, user, state)
        self._remember(thread, user, state)

    def _evaluate(self, thread: str, user: str, state: dict):
        """Score the completed plan and persist/stream the eval report."""
        from travel_agent.evaluation import evaluate

        started = state.get("_started_at")
        latency = (time.time() - started) if started else None
        report = evaluate(state, latency_s=latency, use_judge=True)
        update = {"eval_report": report}
        if report.get("llm_judged"):
            update["llm_calls"] = 1
        self._commit(thread, user, state, update)
        try:
            self.score_log.add(user, (state.get("trip") or {}).get("destination", ""),
                               report.get("overall", 0), report.get("grade", ""))
        except Exception:
            pass
        yield "evaluation", update

    def _remember(self, thread: str, user: str, state: dict) -> None:
        """Save a durable long-term memory of this completed trip and ingest the session into ADK memory."""
        trip = state.get("trip") or {}
        if not trip.get("destination"):
            return
        from datetime import date

        bits = [trip["destination"]]
        if trip.get("num_days"):
            bits.append(f"{trip['num_days']} days")
        if trip.get("origin"):
            bits.append(f"from {trip['origin']}")
        if trip.get("budget"):
            bits.append(f"{trip['budget']} budget")
        if trip.get("interests"):
            bits.append("interests: " + ", ".join(trip["interests"]))
        try:
            self.memory_store.add(user, f"{date.today().isoformat()} - " + ", ".join(bits))
        except Exception:
            pass
        if self._mem is not None:
            try:
                sess = self._loop.run(self._svc.get_session(app_name=APP_NAME, user_id=user, session_id=thread))
                res = self._mem.add_session_to_memory(sess)
                if asyncio.iscoroutine(res):
                    self._loop.run(res)
            except Exception:
                pass

    # ----- reads -----
    def get_values(self, thread_id: str) -> dict:
        return self._state(thread_id)

    def history(self, thread_id: str) -> list[dict]:
        return list(self._state(thread_id).get("messages", []))

    def preferences(self, user_id: str) -> list[str]:
        item = self.store.get(("preferences", user_id), "profile")
        return list(item.value.get("items", [])) if item else []

    def clear_preferences(self, user_id: str) -> None:
        self.store.delete(("preferences", user_id), "profile")
