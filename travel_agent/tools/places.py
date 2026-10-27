"""Google Places API (New) text search and Routes API - both optional."""

import requests

from travel_agent.config import GOOGLE_MAPS_API_KEY

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_PRICE = {
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}


def places_search(query: str, max_results: int = 8) -> str:
    """Search Google Places, e.g. 'hotels in Paris' or 'top attractions in Rome'."""
    if not GOOGLE_MAPS_API_KEY:
        return "(Google Places unavailable: GOOGLE_MAPS_API_KEY not set)"
    try:
        resp = requests.post(
            PLACES_URL,
            headers={
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,"
                "places.rating,places.userRatingCount,places.priceLevel",
            },
            json={"textQuery": query, "pageSize": max_results},
            timeout=20,
        )
        data = resp.json()
    except Exception as exc:
        return f"(Google Places request failed: {exc})"

    if "error" in data:
        return f"(Google Places error: {data['error'].get('message')})"

    lines = []
    for p in data.get("places", []):
        name = (p.get("displayName") or {}).get("text", "?")
        rating = p.get("rating")
        reviews = p.get("userRatingCount")
        price = _PRICE.get(p.get("priceLevel", ""), "")
        rating_txt = f", rating {rating} ({reviews} reviews)" if rating else ""
        price_txt = f", price {price}" if price else ""
        lines.append(f"- {name} - {p.get('formattedAddress', '')}{rating_txt}{price_txt}")
    return "\n".join(lines) or "(no places found)"


def travel_time(origin: str, destination: str, mode: str = "TRANSIT") -> str:
    """Approximate travel time between two places via the Google Routes API."""
    if not GOOGLE_MAPS_API_KEY:
        return ""
    try:
        resp = requests.post(
            ROUTES_URL,
            headers={
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
            },
            json={
                "origin": {"address": origin},
                "destination": {"address": destination},
                "travelMode": mode,
            },
            timeout=20,
        )
        routes = resp.json().get("routes", [])
    except Exception:
        return ""
    if not routes:
        return ""
    r = routes[0]
    minutes = round(int(r.get("duration", "0s").rstrip("s")) / 60)
    km = r.get("distanceMeters", 0) / 1000
    return f"{origin} -> {destination}: ~{minutes} min ({km:.1f} km, {mode.lower()})"
