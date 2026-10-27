"""AviationStack MCP server (LOCAL MCP). Wraps flight schedules + airport lookup.

Runnable standalone:  python -m mcp_servers.flights_server
"""

from mcp.server.mcpserver import MCPServer

from travel_agent.tools.flights import aviationstack_flights, describe_airport

mcp = MCPServer(name="aviationstack", version="1.0.0", instructions="Flight schedules and airport info.")


@mcp.tool(description="Scheduled flights between two IATA airports (current schedules). Args: dep_iata, arr_iata.")
def flights(dep_iata: str, arr_iata: str) -> str:
    return aviationstack_flights(dep_iata, arr_iata)


@mcp.tool(description="Human-readable description of an airport from its IATA code. Args: iata.")
def airport(iata: str) -> str:
    return describe_airport(iata)


if __name__ == "__main__":
    mcp.run("stdio")
