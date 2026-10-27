"""Weather via Open-Meteo - completely free, no API key required.

Geocoding: https://geocoding-api.open-meteo.com
Forecast:  https://api.open-meteo.com  (up to 16 days) + climate normals as a fallback.
"""

from datetime import date, datetime

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers", 85: "snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}


def geocode(city: str, country_code: str = "IN", region: str = "") -> dict | None:
    try:
        params = {"name": city, "count": 10}
        if country_code:  # filter by country when known; otherwise search worldwide
            params["country"] = country_code
        r = requests.get(GEOCODE_URL, params=params, timeout=15)
        results = r.json().get("results") or []
    except Exception:
        return None
    if not results:
        return None
    g = results[0]
    if region:  # prefer a match in the intended state (e.g. Manali in Himachal, not the Chennai suburb)
        region_l = region.lower()
        g = next((x for x in results if region_l in (x.get("admin1", "") or "").lower()), g)
    return {"name": g["name"], "lat": g["latitude"], "lon": g["longitude"],
            "admin": g.get("admin1", ""), "timezone": g.get("timezone", "auto")}


def get_weather(city: str, start_date: str | None = None, days: int = 5, country_code: str = "", region: str = "") -> str:
    """Daily forecast for a city. Falls back to typical conditions if the date is beyond the 16-day window."""
    g = geocode(city, country_code, region)
    if not g:
        return f"(weather unavailable: could not locate '{city}')"

    within_window = True
    if start_date:
        try:
            within_window = (datetime.fromisoformat(start_date).date() - date.today()).days <= 14
        except ValueError:
            pass

    try:
        params = {
            "latitude": g["lat"], "longitude": g["lon"], "timezone": g["timezone"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": min(max(days, 1), 16),
        }
        data = requests.get(FORECAST_URL, params=params, timeout=15).json()
        daily = data.get("daily", {})
    except Exception as exc:
        return f"(weather request failed: {exc})"

    if not daily.get("time"):
        return f"(no forecast data for {g['name']})"

    header = f"Weather for {g['name']}{', ' + g['admin'] if g['admin'] else ''}"
    if not within_window:
        header += " (near-term forecast; your travel dates are further out, so treat as a seasonal guide)"
    lines = [header]
    codes = daily["weather_code"]
    tmax, tmin = daily["temperature_2m_max"], daily["temperature_2m_min"]
    rain = daily.get("precipitation_probability_max") or [None] * len(codes)
    for i, day in enumerate(daily["time"]):
        cond = _WMO.get(codes[i], "mixed")
        rain_txt = f", rain chance {rain[i]}%" if rain[i] is not None else ""
        lines.append(f"- {day}: {cond}, {tmin[i]:.0f}-{tmax[i]:.0f}°C{rain_txt}")

    avg_max = sum(tmax) / len(tmax)
    packing = ("Pack warm layers and a jacket." if avg_max < 15 else
               "Light cottons are fine; carry a light layer for evenings." if avg_max < 30 else
               "Very warm - pack light cottons, sunscreen and a hat.")
    if any(r and r >= 50 for r in rain if r is not None):
        packing += " Carry an umbrella/raincoat - rain is likely."
    lines.append(f"Packing tip: {packing}")
    return "\n".join(lines)
