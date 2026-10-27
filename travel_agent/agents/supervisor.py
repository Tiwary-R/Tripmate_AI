"""Supervisor Agent - understands the request, extracts trip_constraints, and dynamically decides which
specialist agents are needed. No more manual workflow definition.

Also enforces the India-only policy and loads/saves long-term user preferences.
"""

from datetime import date, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from travel_agent import demo
from travel_agent.config import DEMO_MODE, TRAVEL_SCOPE
from travel_agent.india import OUT_OF_SCOPE, country_for_iata, out_of_scope, resolve_airport
from travel_agent.llm import get_structured_llm
from travel_agent.state import SPECIALIST_AGENTS, SupervisorDecision, TravelState, TripDetails

_SCOPE_LINE = {
    "india": "You plan trips WITHIN INDIA only.",
    "global": "You plan trips to ANY country worldwide.",
}.get(TRAVEL_SCOPE, "You plan trips to ANY country worldwide.")

EXTRACT_SYSTEM = """You are the supervisor of a travel planner. {scope} Today is {today}.
Extract structured trip constraints from the request.
- Resolve relative dates ("next month", "in December") into YYYY-MM-DD.
- If this is a follow-up, start from the previous constraints and apply only the requested changes.
- Fill origin_iata / destination_iata with the NEAREST major airport IATA code (e.g. Paris -> CDG, Tokyo -> HND, Manali -> KUU).
- Fill origin_country / destination_country with the ISO alpha-2 country code (e.g. IN, FR, JP, AE). Do not guess.
- Put only lasting personal preferences in new_preferences.
- Set clarification_question only when the destination is truly missing.

Previous constraints (may be empty): {previous}
Known user preferences: {preferences}"""

SELECT_SYSTEM = """You are the supervisor. Given the trip constraints, choose which specialist agents to run.
Available agents:
- flight_agent: flights/trains to the destination. Skip if no origin city is given.
- hotel_agent: where to stay.
- weather_agent: forecast and packing advice (free, always cheap to include).
- budget_agent: cost estimate and money tips. Include when a budget or budget-consciousness is implied.
- itinerary_agent: day-by-day plan of places and activities (almost always useful).
Pick the minimal useful set. Most trip requests need hotel_agent, weather_agent and itinerary_agent at least."""


def _pref_namespace(user_id: str) -> tuple:
    return ("preferences", user_id)


def _extract(state: TravelState, preferences: list[str]) -> TripDetails:
    return get_structured_llm(TripDetails).invoke(
        [
            SystemMessage(
                content=EXTRACT_SYSTEM.format(
                    scope=_SCOPE_LINE,
                    today=date.today().isoformat(),
                    previous=state.get("trip") or "{}",
                    preferences="; ".join(preferences) or "none",
                )
            ),
            HumanMessage(content=state["user_query"]),
        ]
    )


def _rule_select(trip: dict) -> list[str]:
    agents = ["hotel_agent", "weather_agent", "itinerary_agent"]
    if trip.get("origin"):
        agents.insert(0, "flight_agent")
    if trip.get("budget") or trip.get("travelers"):
        agents.append("budget_agent")
    return [a for a in SPECIALIST_AGENTS if a in agents]  # keep canonical order


def _llm_select(trip: dict) -> tuple[list[str], str]:
    try:
        decision: SupervisorDecision = get_structured_llm(SupervisorDecision).invoke(
            [SystemMessage(content=SELECT_SYSTEM), ("human", f"Trip constraints: {trip}")]
        )
        chosen = [a for a in SPECIALIST_AGENTS if a in decision.selected_agents]
        if "flight_agent" in chosen and not trip.get("origin"):
            chosen.remove("flight_agent")
        return (chosen or _rule_select(trip)), (decision.reasoning or "")
    except Exception:
        return _rule_select(trip), ""




def supervisor_node(state: TravelState, *, store, user_id: str = "default") -> dict:
    user_id = state.get("user_id") or user_id
    item = store.get(_pref_namespace(user_id), "profile")
    preferences: list[str] = list(item.value.get("items", [])) if item else []

    llm_calls = 0
    if DEMO_MODE:
        details = demo.parse_request(state["user_query"], state.get("trip"))
    else:
        try:
            details = _extract(state, preferences)
            llm_calls += 1
        except Exception:
            details = TripDetails()
        rules = demo.parse_request(state["user_query"], state.get("trip"))
        for field in ("origin", "destination", "num_days", "travelers", "budget"):
            if not getattr(details, field) and getattr(rules, field):
                setattr(details, field, getattr(rules, field))
        details.new_preferences = list(dict.fromkeys(details.new_preferences + rules.new_preferences))
        if details.destination:
            details.clarification_question = None

    new_prefs = [p for p in details.new_preferences if p and p not in preferences]
    if new_prefs:
        preferences += new_prefs
        store.put(_pref_namespace(user_id), "profile", {"items": preferences})

    trip = details.model_dump(exclude={"new_preferences", "clarification_question"})
    trip["origin_iata"] = resolve_airport(trip.get("origin"), trip.get("origin_iata"))
    trip["destination_iata"] = resolve_airport(trip.get("destination"), trip.get("destination_iata"))
    # Fill country codes from the resolved airport when the LLM left them blank (helps weather + currency).
    trip["origin_country"] = trip.get("origin_country") or country_for_iata(trip.get("origin_iata"))
    trip["destination_country"] = trip.get("destination_country") or country_for_iata(trip.get("destination_iata"))
    if not trip.get("num_days") and trip.get("start_date") and trip.get("end_date"):
        try:
            d = (datetime.fromisoformat(trip["end_date"]) - datetime.fromisoformat(trip["start_date"])).days + 1
            trip["num_days"] = max(d, 1)
        except ValueError:
            pass
    trip["num_days"] = trip.get("num_days") or 3

    base = {
        "user_id": user_id,
        "preferences": preferences,
        "messages": [HumanMessage(content=state["user_query"])],
        "llm_calls": llm_calls,
        "flight_results": "", "hotel_results": "", "weather_info": "",
        "budget_analysis": "", "itinerary": "", "final_response": "",
    }

    # Policy / clarification: stop before selecting agents.
    if not trip.get("destination"):
        return {**base, "trip": state.get("trip") or {}, "selected_agents": [],
                "supervisor_reasoning": "Destination missing - asking the user.",
                "final_response": details.clarification_question or "Where would you like to travel, and for how many days?"}
    for place_key in ("destination", "origin"):
        place = trip.get(place_key)
        if place and out_of_scope(place, trip.get(f"{place_key}_country")):
            msg = OUT_OF_SCOPE.format(place=place)
            if place_key == "origin":
                msg += "\n\nI can still plan the India part - tell me which Indian city you'll start from."
            return {**base, "trip": state.get("trip") or {}, "selected_agents": [],
                    "supervisor_reasoning": f"{place} is outside the configured scope.", "final_response": msg}

    if DEMO_MODE:
        selected, reasoning = _rule_select(trip), "Selected agents based on the trip details."
    else:
        selected, reasoning = _llm_select(trip)
        llm_calls += 1
        base["llm_calls"] = llm_calls

    return {**base, "trip": trip, "selected_agents": selected,
            "supervisor_reasoning": reasoning or "Selected the specialists this trip needs."}
