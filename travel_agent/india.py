"""India-only scope: recognise Indian places, map them to the nearest airport, reject foreign trips."""

import re
import unicodedata
from functools import lru_cache
from typing import Optional

import pycountry

from travel_agent.tools.flights import _airports

# Popular Indian cities / destinations -> nearest commercial airport (IATA).
INDIA_PLACES = {
    # metros & major cities
    "delhi": "DEL", "new delhi": "DEL", "gurgaon": "DEL", "gurugram": "DEL", "noida": "DEL",
    "mumbai": "BOM", "bombay": "BOM", "navi mumbai": "BOM", "bangalore": "BLR", "bengaluru": "BLR",
    "chennai": "MAA", "madras": "MAA", "kolkata": "CCU", "calcutta": "CCU", "hyderabad": "HYD",
    "pune": "PNQ", "ahmedabad": "AMD", "lucknow": "LKO", "chandigarh": "IXC", "kochi": "COK",
    "cochin": "COK", "indore": "IDR", "bhopal": "BHO", "nagpur": "NAG", "patna": "PAT",
    "bhubaneswar": "BBI", "guwahati": "GAU", "trivandrum": "TRV", "thiruvananthapuram": "TRV",
    "coimbatore": "CJB", "visakhapatnam": "VTZ", "vizag": "VTZ", "surat": "STV", "ranchi": "IXR",
    "dehradun": "DED", "raipur": "RPR", "mangalore": "IXE", "vadodara": "BDQ", "jammu": "IXJ",
    "madurai": "IXM", "tirupati": "TIR", "kanpur": "KNU", "prayagraj": "IXD", "allahabad": "IXD",
    # leisure destinations
    "goa": "GOI", "north goa": "GOX", "south goa": "GOI", "jaipur": "JAI", "udaipur": "UDR",
    "jodhpur": "JDH", "jaisalmer": "JSA", "pushkar": "JAI", "agra": "AGR", "varanasi": "VNS",
    "rishikesh": "DED", "haridwar": "DED", "mussoorie": "DED", "auli": "DED", "nainital": "PGH",
    "manali": "KUU", "kullu": "KUU", "kasol": "KUU", "spiti": "KUU", "shimla": "SLV",
    "dharamshala": "DHM", "mcleodganj": "DHM", "amritsar": "ATQ", "srinagar": "SXR", "kashmir": "SXR",
    "gulmarg": "SXR", "pahalgam": "SXR", "leh": "IXL", "ladakh": "IXL", "kerala": "COK",
    "munnar": "COK", "alleppey": "COK", "alappuzha": "COK", "kovalam": "TRV", "varkala": "TRV",
    "wayanad": "CCJ", "ooty": "CJB", "kodaikanal": "IXM", "coorg": "IXE", "mysore": "MYQ",
    "mysuru": "MYQ", "hampi": "VDY", "gokarna": "GOI", "pondicherry": "MAA", "puducherry": "MAA",
    "mahabalipuram": "MAA", "rameswaram": "IXM", "darjeeling": "IXB", "gangtok": "IXB",
    "sikkim": "IXB", "shillong": "SHL", "meghalaya": "SHL", "kaziranga": "JRH", "tawang": "GAU",
    "andaman": "IXZ", "port blair": "IXZ", "havelock": "IXZ", "lakshadweep": "AGX",
    "khajuraho": "HJR", "rann of kutch": "BHJ", "kutch": "BHJ", "mahabaleshwar": "PNQ",
    "lonavala": "PNQ", "aurangabad": "IXU", "ajanta": "IXU", "ellora": "IXU", "mount abu": "UDR",
    "ranthambore": "JAI", "jim corbett": "PGH", "rajasthan": "JAI", "himachal": "KUU",
    "uttarakhand": "DED", "kedarnath": "DED", "badrinath": "DED", "bodh gaya": "GAY", "puri": "BBI",
}


# State hint for towns Open-Meteo tends to mis-geocode (shares a name with a bigger place).
POPULAR_REGION = {
    "manali": "Himachal Pradesh", "shimla": "Himachal Pradesh", "kasol": "Himachal Pradesh",
    "kullu": "Himachal Pradesh", "spiti": "Himachal Pradesh", "dharamshala": "Himachal Pradesh",
    "mcleodganj": "Himachal Pradesh", "munnar": "Kerala", "alleppey": "Kerala", "alappuzha": "Kerala",
    "wayanad": "Kerala", "kovalam": "Kerala", "varkala": "Kerala", "ooty": "Tamil Nadu",
    "kodaikanal": "Tamil Nadu", "coorg": "Karnataka", "hampi": "Karnataka", "gokarna": "Karnataka",
    "rishikesh": "Uttarakhand", "nainital": "Uttarakhand", "mussoorie": "Uttarakhand", "auli": "Uttarakhand",
    "darjeeling": "West Bengal", "gangtok": "Sikkim", "leh": "Ladakh", "gulmarg": "Jammu and Kashmir",
    "pahalgam": "Jammu and Kashmir", "udaipur": "Rajasthan", "jaisalmer": "Rajasthan", "pushkar": "Rajasthan",
    "mount abu": "Rajasthan", "lonavala": "Maharashtra", "mahabaleshwar": "Maharashtra",
}


def region_hint(city: str | None) -> str:
    return POPULAR_REGION.get(_clean(city), "") if city else ""


@lru_cache
def _indian_states() -> set[str]:
    return {_clean(s.name) for s in pycountry.subdivisions.get(country_code="IN")}


@lru_cache
def _foreign_countries() -> set[str]:
    names = set()
    for c in pycountry.countries:
        if c.alpha_2 != "IN":
            names.add(c.name.lower())
            if getattr(c, "common_name", None):
                names.add(c.common_name.lower())
    return names | {"usa", "us", "uk", "america", "england", "europe", "dubai", "bali", "maldives"}


def _clean(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()  # "Nādu" -> "Nadu"
    return re.sub(r"\s+", " ", ascii_name.strip().lower())


def is_indian_place(name: Optional[str]) -> Optional[bool]:
    """True if in India, False if clearly abroad, None if unknown."""
    if not name:
        return None
    n = _clean(name)
    if n in INDIA_PLACES or n in _indian_states() or n == "india":
        return True
    if n in _foreign_countries():
        return False
    countries = {a["country"] for a in _airports().values() if a["city"].lower() == n}
    if "IN" in countries:
        return True
    if countries:
        return False
    return None


def nearest_airport(name: Optional[str], suggested: Optional[str] = None) -> Optional[str]:
    """Nearest Indian airport for a place. Prefers the curated table, then a valid Indian LLM suggestion."""
    if not name:
        return None
    n = _clean(name)
    if n in INDIA_PLACES:
        return INDIA_PLACES[n]
    airports = _airports()
    if suggested and airports.get(suggested.upper(), {}).get("country") == "IN":
        return suggested.upper()
    matches = [c for c, a in airports.items() if a["country"] == "IN" and a["city"].lower() == n]
    return matches[0] if matches else None


def resolve_airport(name: Optional[str], suggested: Optional[str] = None) -> Optional[str]:
    """Resolve the nearest airport for a place, worldwide. Uses the curated India table as an override,
    then the LLM-suggested IATA (validated globally), then a global city-name match."""
    if not name:
        return None
    n = _clean(name)
    if n in INDIA_PLACES:  # curated India overrides stay accurate
        return INDIA_PLACES[n]
    from travel_agent.tools.flights import resolve_iata  # global airportsdata lookup

    return resolve_iata(name, suggested)


def country_for_iata(iata: Optional[str]) -> Optional[str]:
    """ISO alpha-2 country code for an airport IATA code, via airportsdata (worldwide)."""
    if not iata:
        return None
    a = _airports().get(iata.upper())
    return a["country"] if a else None


def out_of_scope(place: Optional[str], llm_country: Optional[str]) -> bool:
    """Whether a place is outside the configured travel scope. Global scope never blocks; India scope blocks
    anything not in India."""
    from travel_agent.config import TRAVEL_SCOPE

    if TRAVEL_SCOPE != "india":
        return False
    known = is_indian_place(place)
    if known is not None:
        return not known
    return bool(llm_country) and llm_country.upper() != "IN"


def find_places(text: str) -> list[tuple[int, str]]:
    """Known Indian/foreign place names mentioned in text, as (position, name), longest names first."""
    t = text.lower()
    found, taken = [], set()
    for name in sorted(list(INDIA_PLACES) + list(_foreign_countries()), key=len, reverse=True):
        if len(name) < 3:
            continue
        for m in re.finditer(r"\b" + re.escape(name) + r"\b", t):
            span = set(range(m.start(), m.end()))
            if span & taken:
                continue
            taken |= span
            found.append((m.start(), name))
    return sorted(found)


OUT_OF_SCOPE = (
    "🇮🇳 Sorry, I currently plan **trips within India only**. **{place}** looks like it's outside India.\n\n"
    "Try a domestic trip, for example *\"4 days in Goa from Bengaluru\"*, *\"Manali from Delhi for 5 days\"* "
    "or *\"a Rajasthan trip covering Jaipur and Udaipur\"*."
)
