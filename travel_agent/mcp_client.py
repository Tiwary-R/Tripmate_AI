"""Synchronous facade over the MCP servers.

Agents call `mcp_call("weather", "forecast", city=...)`. The call goes through the real MCP protocol
(in-process transport) to the servers in `mcp_servers/`. If MCP is disabled or anything fails, it falls
back transparently to calling the same underlying tool function directly, so the app never breaks.
"""

import asyncio
import logging
import os
import threading
from contextlib import AsyncExitStack

log = logging.getLogger(__name__)

USE_MCP = os.getenv("USE_MCP", "true").lower() not in {"0", "false", "no"}

# (server, tool) -> direct fallback callable. Imported lazily to avoid heavy imports at module load.
_FALLBACKS = {
    ("weather", "forecast"): ("travel_agent.tools.weather", "get_weather"),
    ("flights", "flights"): ("travel_agent.tools.flights", "aviationstack_flights"),
    ("flights", "airport"): ("travel_agent.tools.flights", "describe_airport"),
    ("search", "search"): ("travel_agent.tools.search", "web_search"),
    ("search", "places"): ("travel_agent.tools.places", "places_search"),
}
_SERVER_MODULES = {
    "weather": "mcp_servers.weather_server",
    "flights": "mcp_servers.flights_server",
    "search": "mcp_servers.search_server",
}


def _fallback(server: str, tool: str, kwargs: dict) -> str:
    mod_name, func_name = _FALLBACKS[(server, tool)]
    import importlib

    func = getattr(importlib.import_module(mod_name), func_name)
    return func(**kwargs)


class _McpRuntime:
    """Owns a background asyncio loop that keeps the MCP client sessions open."""

    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clients: dict[str, object] = {}
        self._available: dict[str, bool] = {}
        self._stack: AsyncExitStack | None = None
        self._started = False
        self._lock = threading.Lock()

    def _start(self):
        with self._lock:
            if self._started:
                return
            self._started = True
            self._loop = asyncio.new_event_loop()
            threading.Thread(target=self._loop.run_forever, daemon=True, name="mcp-loop").start()
            fut = asyncio.run_coroutine_threadsafe(self._connect_all(), self._loop)
            try:
                fut.result(timeout=30)
            except Exception as exc:  # pragma: no cover
                log.warning("MCP init failed, using direct tool calls: %s", exc)

    async def _connect_all(self):
        from mcp.client import Client

        self._stack = AsyncExitStack()
        import importlib

        for name, module_path in _SERVER_MODULES.items():
            try:
                server = importlib.import_module(module_path).mcp
                client = await self._stack.enter_async_context(Client(server))
                await client.list_tools()
                self._clients[name] = client
                self._available[name] = True
            except Exception as exc:
                self._available[name] = False
                log.warning("MCP server '%s' unavailable (%s); direct fallback will be used.", name, exc)

    def call(self, server: str, tool: str, **kwargs) -> str:
        if not USE_MCP:
            return _fallback(server, tool, kwargs)
        self._start()
        client = self._clients.get(server)
        if client is None:
            return _fallback(server, tool, kwargs)
        try:
            fut = asyncio.run_coroutine_threadsafe(client.call_tool(tool, kwargs), self._loop)
            res = fut.result(timeout=40)
            if getattr(res, "content", None):
                text = getattr(res.content[0], "text", None)
                if text is not None:
                    return text
            sc = getattr(res, "structuredContent", None)
            return str(sc) if sc is not None else ""
        except Exception as exc:
            log.warning("MCP call %s.%s failed (%s); using direct fallback.", server, tool, exc)
            return _fallback(server, tool, kwargs)

    def status(self) -> dict:
        if not USE_MCP:
            return {"enabled": False, "servers": {}}
        self._start()
        return {"enabled": True, "servers": dict(self._available)}


_runtime = _McpRuntime()


def mcp_call(server: str, tool: str, **kwargs) -> str:
    return _runtime.call(server, tool, **kwargs)


def mcp_status() -> dict:
    return _runtime.status()
