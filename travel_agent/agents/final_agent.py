"""4. Final Response Agent - combines all information and generates the final travel plan."""

from langchain_core.messages import AIMessage

from langchain_core.messages import AIMessage

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent import demo
from travel_agent.config import DEMO_MODE
from travel_agent.mcp_client import mcp_call
from travel_agent.state import TravelState

SYSTEM = """You are a friendly senior travel agent. Combine the specialist reports into one polished
travel plan in markdown. Only include a section if the relevant report is present. Possible sections:
1. Trip Overview (2-3 lines)
2. Flights & Trains
3. Where to Stay
4. Weather & Packing
5. Day-by-Day Itinerary
6. Estimated Budget (keep the budget agent's table)
7. Practical Tips (visa/entry requirements and permits where relevant, local transport, currency & payment, safety)
Keep the specialists' facts; remove repetition; do not invent prices beyond their estimates. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def final_agent(state: TravelState) -> dict:
    # The planner already asked a clarification question - pass it through.
    if state.get("final_response"):
        question = state["final_response"]
        return {"final_response": question, "messages": [AIMessage(content=question)]}

    if DEMO_MODE:
        answer = demo.final(state)
        return {"final_response": answer, "messages": [AIMessage(content=answer)]}

    trip = state["trip"]
    tips = mcp_call(
        "search", "search",
        query=f"{trip['destination']} India travel tips permits local transport safety {trip.get('start_date') or ''}",
        max_results=4,
    )
    sections = [("Flights & Trains", state.get("flight_results")), ("Hotels", state.get("hotel_results")),
                ("Weather & Packing", state.get("weather_info")), ("Itinerary", state.get("itinerary")),
                ("Budget", state.get("budget_analysis"))]
    reports = "\n\n".join(f"## {name} report\n{text}" for name, text in sections if text)
    user = f"Trip:\n{trip_summary(state)}\n\n{reports}\n\n## Travel tips search\n{tips}"
    answer = ask_llm(SYSTEM, user)
    return {"final_response": answer, "messages": [AIMessage(content=answer)], "llm_calls": 1}
