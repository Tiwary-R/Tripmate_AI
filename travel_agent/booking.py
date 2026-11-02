"""Booking & multi-provider price comparison (pure, offline, no API keys).

The app has no live pricing source (AviationStack = schedules only, Google
Places = coarse $ buckets), and real rates from Booking.com / MakeMyTrip /
Skyscanner need paid partner APIs. So instead of inventing prices we:

  * surface ONE indicative estimate parsed from our own planner output
    (clearly labelled an estimate, not a live quote), and
  * deep-link into each provider's real, prefilled search page so the user can
    compare live rates and complete the booking on the provider's own site.

Everything here is a pure string function of the ``trip`` dict plus the
specialist markdown already in state — deterministic, network-free, testable.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- estimates --
_CUR = r"(?:₹|Rs\.?|INR|US\$|\$|USD|€|EUR|£|GBP|AED|SGD|THB|¥|JPY)"
_AMT = r"\d[\d,]*(?:\.\d+)?"
_ESTIMATE_RX = re.compile(
    rf"({_CUR})\s?({_AMT})(?:\s?(?:-|–|—|to)\s?({_CUR})?\s?({_AMT}))?",
    re.IGNORECASE,
)


def estimate_from_markdown(md: str | None) -> str | None:
    """Return the first currency amount/range found in a markdown string.

    e.g. ``"... ₹4,500-6,500 ..."`` -> ``"₹4,500–6,500"``; ``None`` when nothing
    parseable (graceful — the UI then just shows the compare links).
    """
    if not md:
        return None
    m = _ESTIMATE_RX.search(md)
    if not m:
        return None
    cur, low, _cur2, high = m.group(1), m.group(2), m.group(3), m.group(4)
    cur = cur.strip()
    if high:
        return f"{cur}{low}–{high}"
    return f"{cur}{low}"


# -------------------------------------------------------------------- dates --
def _parse(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _start(trip: dict) -> date | None:
    return _parse(trip.get("start_date"))


def _checkout(trip: dict) -> date | None:
    """End/return date: explicit end_date, else start + num_days."""
    end = _parse(trip.get("end_date"))
    if end:
        return end
    start = _start(trip)
    if start:
        days = trip.get("num_days") or 1
        try:
            return start + timedelta(days=int(days))
        except (ValueError, TypeError):
            return start + timedelta(days=1)
    return None


def _ymd(d: date | None) -> str:
    return d.strftime("%Y-%m-%d") if d else ""


def _yymmdd(d: date | None) -> str:
    return d.strftime("%y%m%d") if d else ""


def _dmy(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


# ------------------------------------------------------------------- helpers --
def _q(value) -> str:
    return urllib.parse.quote(str(value or ""))


def _qs(params: dict) -> str:
    """Build a query string, dropping empty values."""
    items = [(k, v) for k, v in params.items() if v not in (None, "", 0)]
    return urllib.parse.urlencode(items, safe="/")


def _is_india(trip: dict) -> bool:
    cc = (trip.get("destination_country") or "").upper()
    return cc == "IN"


def _adults(trip: dict) -> int:
    try:
        return max(1, int(trip.get("travelers") or 1))
    except (ValueError, TypeError):
        return 1


# ------------------------------------------------------------------ flights --
def flight_providers(trip: dict) -> list[dict]:
    """Prefilled flight-search links. Provider set auto-selected by destination."""
    origin = trip.get("origin") or ""
    dest = trip.get("destination") or ""
    oi = (trip.get("origin_iata") or "").upper()
    di = (trip.get("destination_iata") or "").upper()
    start, end = _start(trip), _checkout(trip)
    adults = _adults(trip)

    if not origin:
        return []  # no departure city -> nothing to book

    # --- links that work everywhere -----------------------------------------
    gf_q = f"Flights from {origin} to {dest}" + (f" on {_ymd(start)}" if start else "")
    google = {
        "name": "Google Flights",
        "url": "https://www.google.com/travel/flights?q=" + _q(gf_q),
        "blurb": "Compare airlines, dates and fare trends.",
    }
    if oi and di:
        sky_url = f"https://www.skyscanner.net/transport/flights/{oi.lower()}/{di.lower()}/"
        if start:
            sky_url += _yymmdd(start) + "/"
            if end:
                sky_url += _yymmdd(end) + "/"
        kayak_url = f"https://www.kayak.com/flights/{oi}-{di}" + (f"/{_ymd(start)}" if start else "")
        if start and end:
            kayak_url += f"/{_ymd(end)}"
    else:
        sky_url = "https://www.skyscanner.net/"
        kayak_url = "https://www.kayak.com/flights"
    skyscanner = {"name": "Skyscanner", "url": sky_url, "blurb": "Cheapest fares across airlines & agents."}
    kayak = {"name": "Kayak", "url": kayak_url, "blurb": "Flexible-date fare comparison."}

    if not _is_india(trip):
        return [skyscanner, google, kayak]

    # --- India OTAs ----------------------------------------------------------
    if oi and di and start:
        mmt_url = (
            f"https://www.makemytrip.com/flight/search?itinerary={oi}-{di}-{_dmy(start)}"
            f"&tripType=O&paxType=A-{adults}_C-0_I-0&cabinClass=E"
        )
    else:
        mmt_url = "https://www.makemytrip.com/flights/"
    makemytrip = {"name": "MakeMyTrip", "url": mmt_url, "blurb": "India's largest OTA — flights & fare calendar."}

    if oi and di and start:
        cleartrip_url = "https://www.cleartrip.com/flights/results?" + _qs({
            "from": oi, "to": di, "depart_date": _dmy(start), "adults": adults,
            "childs": 0, "infants": 0, "class": "Economy", "intl": "n",
        })
    else:
        cleartrip_url = "https://www.cleartrip.com/flights"
    cleartrip = {"name": "Cleartrip", "url": cleartrip_url, "blurb": "Clean fare search, quick filters."}

    goibibo = {"name": "Goibibo", "url": "https://www.goibibo.com/flights/",
               "blurb": f"Search {origin} → {dest} (GoCash offers)."}
    yatra = {"name": "Yatra", "url": "https://www.yatra.com/flights",
             "blurb": f"Search {origin} → {dest} fares."}

    return [makemytrip, cleartrip, goibibo, yatra, skyscanner, google]


# -------------------------------------------------------------------- hotels --
def hotel_providers(trip: dict) -> list[dict]:
    """Prefilled hotel-search links. Provider set auto-selected by destination."""
    dest = trip.get("destination") or ""
    if not dest:
        return []
    start, end = _start(trip), _checkout(trip)
    adults = _adults(trip)

    booking = {
        "name": "Booking.com",
        "url": "https://www.booking.com/searchresults.html?" + _qs({
            "ss": dest, "checkin": _ymd(start), "checkout": _ymd(end), "group_adults": adults,
        }),
        "blurb": "Huge inventory, free-cancellation filters.",
    }
    google_hotels = {
        "name": "Google Hotels",
        "url": "https://www.google.com/travel/search?q=" + _q(f"hotels in {dest}"),
        "blurb": "Map view and price comparison.",
    }

    if not _is_india(trip):
        agoda = {"name": "Agoda", "url": "https://www.agoda.com/search?q=" + _q(dest),
                 "blurb": "Strong deals across Asia-Pacific."}
        if start and end:
            kayak_url = f"https://www.kayak.com/hotels/{_q(dest)}/{_ymd(start)}/{_ymd(end)}/{adults}adults"
        else:
            kayak_url = "https://www.kayak.com/hotels"
        kayak_hotels = {"name": "Kayak Hotels", "url": kayak_url, "blurb": "Compare hotel rates by site."}
        return [booking, agoda, google_hotels, kayak_hotels]

    # --- India OTAs ----------------------------------------------------------
    mmt = {
        "name": "MakeMyTrip",
        "url": "https://www.makemytrip.com/hotels/hotel-listing/?" + _qs({
            "searchText": dest,
            "checkin": start.strftime("%Y%m%d") if start else "",
            "checkout": end.strftime("%Y%m%d") if end else "",
            "roomStayQualifier": f"{adults}e0e",
        }),
        "blurb": "India hotels, instant discounts.",
    }
    goibibo = {"name": "Goibibo", "url": "https://www.goibibo.com/hotels/",
               "blurb": f"Hotels in {dest} with GoCash."}
    return [mmt, goibibo, booking, google_hotels]


# ---------------------------------------------------------- export markdown --
def booking_markdown(trip: dict, flight_md: str | None = None, hotel_md: str | None = None) -> str:
    """A markdown 'Booking & price comparison' section for the PDF export."""
    if not trip or not trip.get("destination"):
        return ""
    lines = ["", "---", "", "## Booking & price comparison", ""]
    lines.append("_Prices below are planner estimates, not live quotes. "
                 "Links open each provider's own site to compare live rates and complete booking._")
    lines.append("")

    flights = flight_providers(trip)
    if flights:
        est = estimate_from_markdown(flight_md)
        lines.append("### Flights")
        if est:
            lines.append(f"Indicative fare (estimate): **{est}** per person.")
        for p in flights:
            lines.append(f"- [{p['name']}]({p['url']}) — {p['blurb']}")
        lines.append("")

    hotels = hotel_providers(trip)
    if hotels:
        est = estimate_from_markdown(hotel_md)
        lines.append("### Hotels")
        if est:
            lines.append(f"Indicative rate (estimate): **{est}** per night.")
        for p in hotels:
            lines.append(f"- [{p['name']}]({p['url']}) — {p['blurb']}")
        lines.append("")

    return "\n".join(lines)
