"""Force demo mode (no LLM / network) before any travel_agent module imports config."""

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("USE_MCP", "false")  # tools call direct functions; no MCP subprocess needed
