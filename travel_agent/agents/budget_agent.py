"""Budget Agent - analyzes budget, estimates cost and gives money-saving recommendations (LLM via MCP)."""

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent.config import DEMO_MODE
from travel_agent.state import TravelState
from travel_agent import demo

SYSTEM = """You are a travel budget analyst. Produce an estimated cost breakdown in the destination's LOCAL
CURRENCY (add an approximate USD total) as a markdown table with rows: Flights/Transport, Hotel, Food,
Activities, Local transport, Buffer, and a Total. Base it on the number of travelers, nights and the stated
budget level (budget / mid-range / luxury) and realistic local prices for the destination. Add 2-3
money-saving tips. Note the figures are estimates. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def budget_agent(state: TravelState) -> dict:
    trip = state["trip"]
    if DEMO_MODE:
        return {"budget_analysis": demo.budget(state)}

    context = trip_summary(state)
    if state.get("flight_results"):
        context += "\n\nFlight/train findings:\n" + state["flight_results"][:800]
    if state.get("hotel_results"):
        context += "\n\nHotel findings:\n" + state["hotel_results"][:800]
    return {"budget_analysis": ask_llm(SYSTEM, context), "llm_calls": 1}
