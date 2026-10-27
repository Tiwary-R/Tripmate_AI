"""1. Flight Agent - searches flights and finds the best options."""

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent import demo
from travel_agent.config import DEMO_MODE
from travel_agent.mcp_client import mcp_call
from travel_agent.state import TravelState

SYSTEM = """You are a travel specialist for flights and ground transport (trains/buses). Using the schedule
data and web search results provided, recommend the 3 best options (cheapest, fastest, best value) with
airline/operator, route, duration, stops and an approximate fare in the LOCAL CURRENCY of the route (add an
approximate USD equivalent). If the destination has no airport, name the nearest airport and how to reach the
destination from it. Suggest a good train or bus alternative when practical for the region. Use only what the
data supports; mark estimates. Finish with 2-3 booking tips. Respond in concise markdown. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def flight_agent(state: TravelState) -> dict:
    trip = state["trip"]
    origin, dest = trip.get("origin"), trip.get("destination")
    if not origin:
        return {"flight_results": "_No departure city given, so flights were skipped. "
                                  "Tell me where you're flying from to get flight options._"}

    if DEMO_MODE:
        return {"flight_results": demo.flights(trip)}

    o_iata, d_iata = trip.get("origin_iata"), trip.get("destination_iata")
    route = f"{o_iata or origin} to {d_iata or dest}"
    # Tools via MCP: AviationStack (flights) + Tavily (search)
    schedules = mcp_call("flights", "flights", dep_iata=o_iata, arr_iata=d_iata) if o_iata and d_iata else "(airport codes unknown)"
    when = f" on {trip['start_date']}" if trip.get("start_date") else ""
    search = mcp_call("search", "search", query=f"cheapest flights and trains {origin} to {dest}{when} fare INR duration")

    airports = ""
    if o_iata and d_iata:
        airports = (f"From: {mcp_call('flights', 'airport', iata=o_iata)}\n"
                    f"To: {mcp_call('flights', 'airport', iata=d_iata)}\n")

    user = (
        f"Trip:\n{trip_summary(state)}\n\nRoute: {route}\n{airports}\n"
        f"AviationStack schedules:\n{schedules}\n\nWeb search results:\n{search}"
    )
    return {"flight_results": ask_llm(SYSTEM, user), "llm_calls": 1}
