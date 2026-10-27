"""Tavily MCP server (REMOTE MCP in the architecture - web search).

Wraps Tavily web search and Google Places. Runnable standalone:  python -m mcp_servers.search_server
"""

from mcp.server.mcpserver import MCPServer

from travel_agent.tools.places import places_search
from travel_agent.tools.search import web_search

mcp = MCPServer(name="tavily-search", version="1.0.0", instructions="Web search and places lookup.")


@mcp.tool(description="Web search for up-to-date info (hotels, prices, tips). Args: query, max_results.")
def search(query: str, max_results: int = 5) -> str:
    return web_search(query, max_results)


@mcp.tool(description="Find places (hotels, attractions) via Google Places. Args: query, max_results.")
def places(query: str, max_results: int = 8) -> str:
    return places_search(query, max_results)


if __name__ == "__main__":
    mcp.run("stdio")
