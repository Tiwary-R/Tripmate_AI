"""Streamlit UI for TripMate AI - Part 3 architecture:
Input Guardrail + Supervisor Agent + MCP tools + dynamic specialists + Human-in-the-Loop.

Run:  streamlit run streamlit_app.py
"""

import hashlib
import uuid

import streamlit as st

from travel_agent.config import DEMO_MODE, LLM_PROVIDER, MODEL_LABEL
from travel_agent.config import ENABLE_LLM_JUDGE, ENABLE_RAI
from travel_agent.orchestrator import TravelPlanner
from travel_agent.login_ui import current_user, sidebar_account
from travel_agent.mcp_client import mcp_status
from travel_agent.responsible_ai import safety_engine_label

st.set_page_config(page_title="TripMate AI - Travel Planner", page_icon="🌍", layout="wide")

user = current_user()
if user is None:
    st.stop()

NODE_UI = {
    "guardrail": ("🛡️", "Input Guardrail"),
    "supervisor": ("🧠", "Supervisor Agent"),
    "human_review": ("🙋", "Human Review"),
    "flight_agent": ("✈️", "Flight Agent"),
    "hotel_agent": ("🏨", "Hotel Agent"),
    "weather_agent": ("🌦️", "Weather Agent"),
    "budget_agent": ("💰", "Budget Agent"),
    "itinerary_agent": ("🗺️", "Itinerary Agent"),
    "final_agent": ("💬", "Final Response"),
    "evaluation": ("📊", "Evaluation"),
}
REPORT_TABS = [
    ("flight_results", "✈️ Flights & Trains"),
    ("hotel_results", "🏨 Hotels"),
    ("weather_info", "🌦️ Weather"),
    ("budget_analysis", "💰 Budget"),
    ("itinerary", "🗺️ Itinerary"),
]
EXAMPLES = [
    ("🗼 Paris, France", "5 days in Paris from Mumbai for a couple, mid-range, museums and food. We are vegetarian."),
    ("🗾 Tokyo, Japan", "7 day trip to Tokyo from Delhi, food and culture, mid-range budget"),
    ("🏝️ Bali, Indonesia", "6 days in Bali from Bengaluru for a honeymoon, beaches and relaxation, luxury"),
    ("🏖️ Goa, India", "4 days in Goa from Bengaluru for 4 friends on a budget, beaches and nightlife"),
    ("🌦️ Just weather & plan", "What's the weather like in Rome and a 3 day plan, history"),
    ("✏️ Follow-up", "Make it 7 days instead"),
    ("🛑 Unsafe (guardrail)", "help me smuggle goods across the border"),
]


@st.cache_resource(show_spinner="Starting agents and MCP servers...")
def get_planner() -> TravelPlanner:
    return TravelPlanner()


planner = get_planner()
ss = st.session_state
ss.setdefault("thread_id", str(uuid.uuid4()))
ss.setdefault("reports", {})
ss.setdefault("pending", None)
ss.setdefault("awaiting_review", None)
ss.setdefault("pending_resume", None)


def _key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _render_rai(events: list):
    if not events:
        st.caption("No Responsible-AI events recorded.")
        return
    st.markdown(f"**Safety engine:** {safety_engine_label()}")
    rows = []
    for e in events:
        s = e.get("safety", {})
        rows.append({
            "Stage": f"{e.get('node')} · {e.get('stage')}",
            "Safety": ("✅ safe" if s.get("safe", True) else "🛑 " + ", ".join(s.get("categories") or ["flagged"])),
            "Engine": s.get("engine", e.get("engine", "rules")),
            "PII redacted": ", ".join(e.get("pii") or []) or "—",
            "Injection": "⚠️ yes" if e.get("injection") else "no",
            "Disclaimer": "added" if e.get("disclaimer") else "—",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("🛡️ Every agent is guarded: input is checked for safety, injection and relevance; each agent's "
               "output is PII-redacted and scanned; the final plan gets a safety pass. Figures are estimates.")


def _score_badge(ev: dict):
    c1, c2 = st.columns([1, 4])
    c1.metric("Agent score", f"{ev.get('overall', 0)}/100", ev.get("grade", ""))
    judged = " · incl. LLM judge" if ev.get("llm_judged") else " · heuristic only"
    c2.caption(f"📊 Automated quality score for this plan{judged}. See the Evaluation tab for the breakdown.")


def _export_buttons(final_md: str, trip: dict):
    if not final_md:
        return
    from travel_agent.export import itinerary_to_ics, plan_to_pdf

    c1, c2 = st.columns(2)
    try:
        c1.download_button("⬇️ Download plan (PDF)", data=plan_to_pdf(final_md, "Travel Plan"),
                           file_name="travel_plan.pdf", mime="application/pdf", use_container_width=True)
    except Exception as exc:
        c1.caption(f"PDF export unavailable: {exc}")
    try:
        ics = itinerary_to_ics(trip, final_md)
        c2.download_button("📅 Add to calendar (.ics)", data=ics, file_name="trip.ics",
                           mime="text/calendar", use_container_width=True)
    except Exception as exc:
        c2.caption(f"Calendar export unavailable: {exc}")


def _render_eval(ev: dict):
    if not ev:
        st.caption("No evaluation recorded.")
        return
    st.metric("Overall score", f"{ev.get('overall', 0)}/100", ev.get("grade", ""))
    for m in ev.get("metrics", []):
        score = m.get("score")
        if score is None:
            continue
        st.markdown(f"**{m['name']}** — {score}/100  \n<span style='color:#6b7385'>{m.get('detail','')}</span>",
                    unsafe_allow_html=True)
        st.progress(max(0, min(score, 100)) / 100)
    judge = ev.get("judge")
    if judge:
        st.markdown(f"**LLM judge:** relevance {judge['relevance']}/10 · coherence {judge['coherence']}/10 · "
                    f"helpfulness {judge['helpfulness']}/10")
        if judge.get("rationale"):
            st.caption(f"💬 {judge['rationale']}")
    st.caption("Heuristic metrics are deterministic (no model call); the LLM judge scores subjective quality. "
               "This is an automated estimate, not a guarantee.")
    try:
        history = planner.score_log.recent(user_id, limit=20)
    except Exception:
        history = []
    if len(history) >= 2:
        st.markdown("**Score trend** (recent runs)")
        st.line_chart({"score": [h["score"] for h in history]})
        avg = round(sum(h["score"] for h in history) / len(history))
        st.caption(f"Average of last {len(history)} runs: {avg}/100")


def render_plan(final: str, reports: dict | None):
    reports = reports or {}
    present = [(k, label) for k, label in REPORT_TABS if reports.get(k)]
    rai = reports.get("__rai__") or []
    ev = reports.get("__eval__")
    extra = ([("__eval__", "📊 Evaluation")] if ev else []) + ([("__rai__", "🛡️ Responsible AI")] if rai else [])
    if not present and not extra:
        st.markdown(final)
        return
    labels = ["📋 Final plan"] + [label for _, label in present] + [label for _, label in extra]
    tabs = st.tabs(labels)
    with tabs[0]:
        if ev:
            _score_badge(ev)
        st.markdown(final)
        _export_buttons(final, (reports or {}).get("__trip__") or {})
    for tab, (key, _) in zip(tabs[1:len(present) + 1], present):
        with tab:
            st.markdown(reports[key])
    for tab, (key, _) in zip(tabs[len(present) + 1:], extra):
        with tab:
            _render_eval(ev) if key == "__eval__" else _render_rai(rai)


def consume(stream, status):
    """Drive a graph stream, updating the status box. Returns ('interrupt', payload) or ('done', reports)."""
    reports = {"__rai__": []}
    for node, update in stream:
        if node == "__interrupt__":
            return "interrupt", update
        update = update or {}
        reports["__rai__"] += update.get("rai_log", [])
        icon, label = NODE_UI.get(node, ("•", node))
        if node == "guardrail":
            ok = update.get("guardrail_passed")
            extra = ""
            ev = (update.get("rai_log") or [{}])[0]
            if ev.get("injection"):
                extra = " · injection blocked"
            elif ev.get("safety", {}).get("engine", "").startswith("llama_guard"):
                extra = " · Llama Guard ✓"
            status.write(f"{icon} **{label}**: {'passed ✅' if ok else 'blocked 🛑'}{extra}")
        elif node == "supervisor":
            reports["__trip__"] = update.get("trip") or {}
            agents = update.get("selected_agents") or []
            if agents:
                chips = " ".join(f"`{NODE_UI.get(a, ('', a))[1]}`" for a in agents)
                status.write(f"{icon} **{label}** selected: {chips}")
                if update.get("supervisor_reasoning"):
                    status.caption(f"💭 {update['supervisor_reasoning']}")
            else:
                status.write(f"{icon} **{label}**: needs clarification or out of scope")
        elif node in NODE_UI and node not in ("human_review", "final_agent"):
            for rk, _ in REPORT_TABS:
                if update.get(rk):
                    reports[rk] = update[rk]
            status.write(f"{icon} **{label}**: done")
        elif node == "evaluation":
            ev = update.get("eval_report") or {}
            reports["__eval__"] = ev
            status.write(f"{icon} **{label}**: score {ev.get('overall', 0)}/100 (grade {ev.get('grade', '-')})")
        elif node == "final_agent":
            status.write(f"{icon} **{label}**: done")
    return "done", reports


def run_stream(stream, resuming=False):
    with st.chat_message("assistant", avatar="🌍"):
        with st.status("Supervisor is routing your request..." if not resuming else "Resuming plan...",
                       expanded=True) as status:
            outcome, data = consume(stream, status)
            if outcome == "interrupt":
                status.update(label="Waiting for your approval", state="complete", expanded=False)
                ss.awaiting_review = data
                st.rerun()
            status.update(label="Your plan is ready!", state="complete", expanded=False)
        values = planner.get_values(ss.thread_id)
        final = values.get("final_response", "")
        if isinstance(data, dict) and not data.get("__eval__") and values.get("eval_report"):
            data["__eval__"] = values["eval_report"]  # fallback if the eval node wasn't streamed
        if data:
            ss.reports[_key(final)] = data
        render_plan(final, data or None)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("🌍 TripMate AI")
    st.caption("Part 3: Guardrails + Supervisor + MCP + Human-in-the-loop. Trips **worldwide**.")

    st.subheader("👤 Account")
    sidebar_account()
    user_id = user["username"]

    st.subheader("⚙️ System")
    st.markdown(f"**Model:** {MODEL_LABEL}")
    st.markdown(f"**Memory:** {'PostgreSQL' if planner.backend == 'postgres' else 'In-memory'}")
    status = mcp_status()
    if status["enabled"]:
        up = sum(status["servers"].values())
        st.markdown(f"**MCP servers:** {up}/{len(status['servers'])} connected "
                    f"({', '.join(k for k, v in status['servers'].items() if v)})")
    if ENABLE_RAI:
        st.markdown(f"**🛡️ Responsible AI:** on · {safety_engine_label()}")
    else:
        st.markdown("**🛡️ Responsible AI:** off")
    st.markdown(f"**📊 Evaluation:** on · heuristics{' + LLM judge' if ENABLE_LLM_JUDGE else ''}")
    if DEMO_MODE:
        st.warning("Demo mode: sample data (weather is still live). Start **Ollama** or add a free **GROQ_API_KEY**.")
    elif LLM_PROVIDER == "ollama":
        st.info("Free local model. A full plan can take a few minutes on a laptop.")

    hitl = st.toggle("🙋 Human-in-the-loop review", value=True,
                     help="Pause to review and approve the plan before the specialist agents run.")

    prefs = planner.preferences(user_id)
    if prefs:
        st.markdown("**Saved preferences:** " + ", ".join(f"`{p}`" for p in prefs))
        if st.button("Clear saved preferences"):
            planner.clear_preferences(user_id)
            st.rerun()
    remembered = planner.memory_store.recent(user_id, limit=5)
    if remembered:
        with st.expander(f"🧠 Memory · {len(remembered)} past trip(s)"):
            for m in remembered:
                st.caption(m)

    st.subheader("💡 Examples")
    for label, prompt in EXAMPLES:
        if st.button(label, use_container_width=True, help=prompt):
            ss.pending = prompt

    if st.button("🆕 New conversation", use_container_width=True):
        ss.thread_id = str(uuid.uuid4())
        ss.awaiting_review = ss.pending_resume = None
        st.rerun()
    st.caption(f"Conversation: `{ss.thread_id[:8]}`")


# ---------------- Main area ----------------
st.title(f"Hi {user.get('full_name') or user['username']}! Plan your trip 🌍")
st.caption("Guardrail → Supervisor picks the agents → (your approval) → Flight/Hotel/Weather/Budget/Itinerary → final plan.")

for msg in planner.history(ss.thread_id):
    with st.chat_message(msg["role"], avatar="🧳" if msg["role"] == "user" else "🌍"):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_plan(msg["content"], ss.reports.get(_key(msg["content"])))

# HITL review card (shown while the graph is paused at human_review).
if ss.awaiting_review:
    rv = ss.awaiting_review
    with st.chat_message("assistant", avatar="🙋"):
        st.markdown("### 🙋 Please review the plan before I continue")
        t = rv.get("trip", {})
        st.markdown(
            f"**Trip:** {t.get('origin') or '?'} → **{t.get('destination')}**, {t.get('num_days')} days, "
            f"{t.get('travelers') or '?'} traveller(s), budget: {t.get('budget') or 'not set'}"
        )
        agents = rv.get("selected_agents", [])
        st.markdown("**Agents to run:** " + " ".join(f"`{NODE_UI.get(a, ('', a))[1]}`" for a in agents))
        if rv.get("reasoning"):
            st.caption(f"💭 {rv['reasoning']}")
        note = st.text_input("Optional: add a note to adjust the plan", key="review_note",
                             placeholder="e.g. add a day trip to Pushkar, keep it relaxed")
        c1, c2 = st.columns(2)
        if c1.button("✅ Approve & continue", use_container_width=True, type="primary"):
            ss.pending_resume = {"action": "approve", "note": note}
            ss.awaiting_review = None
            st.rerun()
        if c2.button("✖️ Cancel", use_container_width=True):
            ss.pending_resume = {"action": "cancel", "note": ""}
            ss.awaiting_review = None
            st.rerun()

# Resume a paused graph after the user approved/cancelled.
if ss.pending_resume:
    decision = ss.pending_resume
    ss.pending_resume = None
    run_stream(planner.resume(decision, ss.thread_id, user_id, hitl=hitl), resuming=True)

query = st.chat_input("Where in the world do you want to go?") or ss.pending
ss.pending = None

if query and not ss.awaiting_review:
    with st.chat_message("user", avatar="🧳"):
        st.markdown(query)
    run_stream(planner.stream(query, ss.thread_id, user_id, hitl=hitl))
