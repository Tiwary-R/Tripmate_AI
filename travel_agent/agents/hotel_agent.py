"""2. Hotel Agent - searches hotels and compares options."""

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent import demo
from travel_agent.config import DEMO_MODE
from travel_agent.mcp_client import mcp_call
from travel_agent.state import TravelState

SYSTEM = """You are a hotel-research specialist. Using the Google Places data and web search results
provided, compare and recommend 3-5 hotels across budget levels that fit the traveler's budget and
preferences. For each give name, area/neighbourhood, approximate nightly price in the destination's LOCAL
CURRENCY (add an approximate USD equivalent), rating if known, and why it fits. Add a one-line recommendation
on which area to stay in. Concise markdown. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def hotel_agent(state: TravelState) -> dict:
    trip = state["trip"]
    if DEMO_MODE:
        return {"hotel_results": demo.hotels(trip)}
    dest = trip["destination"]
    budget = trip.get("budget") or ""
    places = mcp_call("search", "places", query=f"best hotels in {dest}")
    search = mcp_call("search", "search", query=f"best {budget} hotels in {dest} price per night reviews")

    user = f"Trip:\n{trip_summary(state)}\n\nGoogle Places:\n{places}\n\nWeb search results:\n{search}"
    return {"hotel_results": ask_llm(SYSTEM, user), "llm_calls": 1}
