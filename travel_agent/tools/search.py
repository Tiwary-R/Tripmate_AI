"""Tavily web search, shared by all agents."""

from langchain_tavily import TavilySearch

from travel_agent.config import TAVILY_API_KEY


def web_search(query: str, max_results: int = 5) -> str:
    """Run a Tavily search and return results as a compact text block."""
    if not TAVILY_API_KEY:
        return "(Tavily search unavailable: TAVILY_API_KEY not set)"
    try:
        response = TavilySearch(max_results=max_results).invoke({"query": query})
    except Exception as exc:  # network / quota errors should not break the plan
        return f"(Tavily search failed: {exc})"

    results = response.get("results", []) if isinstance(response, dict) else []
    if not results:
        return "(no search results)"
    lines = []
    for r in results:
        content = (r.get("content") or "").strip().replace("\n", " ")
        lines.append(f"- {r.get('title', '')} ({r.get('url', '')}): {content[:600]}")
    return "\n".join(lines)
