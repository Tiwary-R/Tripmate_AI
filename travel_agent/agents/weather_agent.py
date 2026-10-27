"""Weather Agent - forecast, climate info and packing suggestions (Custom Weather MCP / Open-Meteo)."""

from travel_agent.agents.common import ask_llm, trip_summary
from travel_agent.config import DEMO_MODE
from travel_agent.india import region_hint
from travel_agent.mcp_client import mcp_call
from travel_agent.state import TravelState
from travel_agent import demo

SYSTEM = """You are a weather and packing specialist. Using the forecast data provided,
give a short weather outlook for the trip, note any rain/heat/cold to plan around, and a concise packing
list tailored to the destination and season. Markdown, under 150 words. Always write strictly about the destination named in the trip; never substitute another city or country.
"""


def weather_agent(state: TravelState) -> dict:
    trip = state["trip"]
    if DEMO_MODE:
        return {"weather_info": demo.weather(trip)}

    dest = trip["destination"]
    forecast = mcp_call(
        "weather", "forecast",
        city=dest, start_date=trip.get("start_date") or "",
        days=min(trip.get("num_days") or 5, 7),
        country_code=trip.get("destination_country") or "", region=region_hint(dest),
    )
    user = f"Trip:\n{trip_summary(state)}\n\nForecast data (Open-Meteo):\n{forecast}"
    return {"weather_info": ask_llm(SYSTEM, user), "llm_calls": 1}
