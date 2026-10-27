"""Airport lookup (airportsdata + pycountry) and AviationStack flight schedules."""

from functools import lru_cache
from typing import Optional

import airportsdata
import pycountry
import requests

from travel_agent.config import AVIATIONSTACK_API_KEY

# The AviationStack free plan only supports plain HTTP.
AVIATIONSTACK_URL = "http://api.aviationstack.com/v1/flights"


@lru_cache
def _airports() -> dict:
    return airportsdata.load("IATA")


def country_name(code: str) -> str:
    country = pycountry.countries.get(alpha_2=code) if code else None
    return country.name if country else code


def describe_airport(iata: str) -> str:
    a = _airports().get(iata.upper())
    if not a:
        return iata
    return f"{a['name']} ({iata.upper()}), {a['city']}, {country_name(a['country'])}"


def resolve_iata(city: Optional[str], suggested: Optional[str] = None) -> Optional[str]:
    """Validate the LLM-suggested IATA code, or fall back to matching the city name."""
    airports = _airports()
    if suggested and suggested.upper() in airports:
        return suggested.upper()
    if not city:
        return None
    city_l = city.strip().lower()
    if len(city_l) == 3 and city_l.upper() in airports:
        return city_l.upper()
    matches = [code for code, a in airports.items() if a["city"].lower() == city_l]
    if not matches:  # e.g. "Delhi" -> "New Delhi"
        matches = [code for code, a in airports.items() if city_l in a["city"].lower()]
    # Prefer airports explicitly named "International" when a city has several.
    matches.sort(key=lambda c: "international" not in airports[c]["name"].lower())
    return matches[0] if matches else None


def aviationstack_flights(dep_iata: str, arr_iata: str, limit: int = 10) -> str:
    """Return scheduled flights on a route from AviationStack (current schedules)."""
    if not AVIATIONSTACK_API_KEY:
        return "(AviationStack unavailable: AVIATIONSTACK_API_KEY not set)"
    try:
        resp = requests.get(
            AVIATIONSTACK_URL,
            params={
                "access_key": AVIATIONSTACK_API_KEY,
                "dep_iata": dep_iata,
                "arr_iata": arr_iata,
                "limit": limit,
            },
            timeout=20,
        )
        data = resp.json()
    except Exception as exc:
        return f"(AviationStack request failed: {exc})"

    if "error" in data:
        return f"(AviationStack error: {data['error'].get('message', data['error'])})"

    seen, lines = set(), []
    for f in data.get("data", []):
        airline = (f.get("airline") or {}).get("name") or "Unknown airline"
        number = (f.get("flight") or {}).get("iata") or ""
        if (airline, number) in seen:
            continue
        seen.add((airline, number))
        dep = (f.get("departure") or {}).get("scheduled") or "?"
        arr = (f.get("arrival") or {}).get("scheduled") or "?"
        lines.append(f"- {airline} {number}: departs {dep}, arrives {arr}")
    return "\n".join(lines) or f"(no direct flights found on {dep_iata} -> {arr_iata} in current schedules)"
