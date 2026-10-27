"""3. Itinerary Agent - creates a day-wise itinerary with places to visit and activities."""

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent import demo
from travel_agent.config import DEMO_MODE
from travel_agent.mcp_client import mcp_call
from travel_agent.state import TravelState

SYSTEM = """You are an expert itinerary planner. Build a realistic day-by-day itinerary with exactly
{days} days. For each day give Morning / Afternoon / Evening with specific places, activities and a
food suggestion, grouping nearby sights together to reduce travel. Respect the traveler's interests
and saved preferences, local festivals, opening hours and the season/climate of the destination.
Use the attraction data provided. Concise markdown with a heading per day. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def itinerary_agent(state: TravelState) -> dict:
    trip = state["trip"]
    if DEMO_MODE:
        return {"itinerary": demo.itinerary(trip)}
    dest = trip["destination"]
    interests = ", ".join(trip.get("interests") or []) or "highlights"
    attractions = mcp_call("search", "places", query=f"top tourist attractions in {dest}")
    search = mcp_call("search", "search", query=f"{trip['num_days']} day itinerary {dest} {interests} must-see things to do")

    weather = f"\n\nWeather outlook (plan around this):\n{state['weather_info']}" if state.get("weather_info") else ""
    user = (
        f"Trip:\n{trip_summary(state)}\n\nGoogle Places attractions:\n{attractions}\n\n"
        f"Web search results:\n{search}{weather}"
    )
    return {"itinerary": ask_llm(SYSTEM.format(days=trip["num_days"]), user, temperature=0.5), "llm_calls": 1}
