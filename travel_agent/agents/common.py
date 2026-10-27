from langchain_core.messages import HumanMessage, SystemMessage

from travel_agent.llm import get_llm


def trip_summary(state: dict) -> str:
    trip = state.get("trip", {})
    dest = trip.get("destination")
    country = trip.get("destination_country")
    header = ""
    if dest:  # pin every agent to the exact destination (small models otherwise drift)
        header = f"DESTINATION (write ONLY about this place): {dest}" + (f", {country}" if country else "") + "\n"
    fields = [
        ("Origin", trip.get("origin")),
        ("Destination", f"{dest}, {country}" if dest and country else dest),
        ("Dates", f"{trip.get('start_date') or '?'} to {trip.get('end_date') or '?'}"),
        ("Days", trip.get("num_days")),
        ("Travelers", trip.get("travelers")),
        ("Budget", trip.get("budget")),
        ("Interests", ", ".join(trip.get("interests") or []) or None),
        ("Saved user preferences", "; ".join(state.get("preferences") or []) or None),
        ("Remembered past trips", state.get("recalled_memory") or None),
        ("Extra note from traveller", state.get("hitl_feedback") or None),
    ]
    return header + "\n".join(f"{k}: {v}" for k, v in fields if v)


def ask_llm(system: str, user: str, temperature: float = 0.3) -> str:
    from travel_agent.config import ENABLE_RAI
    from travel_agent.responsible_ai import FAIRNESS_NOTE

    if ENABLE_RAI:
        system = system + FAIRNESS_NOTE  # transparency & fairness pillar, applied to every agent
    response = get_llm(temperature).invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return response.content
