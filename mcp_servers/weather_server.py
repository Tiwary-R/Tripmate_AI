"""Custom Weather MCP server (LOCAL CUSTOM MCP in the architecture).

Wraps the free Open-Meteo weather tool. Runnable standalone:  python -m mcp_servers.weather_server
"""

from mcp.server.mcpserver import MCPServer

from travel_agent.tools.weather import get_weather

mcp = MCPServer(name="custom-weather", version="1.0.0", instructions="Free weather forecasts via Open-Meteo.")


@mcp.tool(description="Daily weather forecast and packing advice for a city worldwide. Args: city, start_date (YYYY-MM-DD, optional), days, country_code (ISO alpha-2, optional), region (state hint, optional).")
def forecast(city: str, start_date: str = "", days: int = 5, country_code: str = "", region: str = "") -> str:
    return get_weather(city, start_date or None, days, country_code=country_code, region=region)


if __name__ == "__main__":
    mcp.run("stdio")
