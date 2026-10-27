"""Demo mode: offline stand-ins for the LLM so the whole UI can be explored without any model.

The planner uses a rule-based parser and each agent returns destination-aware sample content for India.
"""

import re
import time
from datetime import date, timedelta

from travel_agent.india import INDIA_PLACES, find_places
from travel_agent.state import TripDetails

AGENT_DELAY_SECONDS = 1.5  # makes the parallel agent progress visible in the UI

CITY_DATA = {
    "goa": {
        "state": "Goa", "area": "North Goa (Candolim/Anjuna) for nightlife or South Goa (Palolem) for quiet beaches",
        "season": "November-February is peak season; monsoon (June-September) is lush but many shacks close.",
        "hotels": [("Taj Fort Aguada Resort & Spa", "Candolim", "₹18,000-30,000", 4.6),
                   ("Novotel Goa Resort", "Candolim", "₹8,000-12,000", 4.4),
                   ("Ciarans Beach Huts", "Palolem", "₹4,000-7,000", 4.2),
                   ("The Hosteller Goa", "Anjuna", "₹1,200-3,000", 4.3)],
        "sights": ["Baga & Calangute beaches", "Fort Aguada", "Old Goa churches (Basilica of Bom Jesus)",
                   "Anjuna flea market (Wednesday)", "Dudhsagar Falls", "Fontainhas Latin Quarter, Panjim",
                   "Chapora Fort", "Palolem Beach", "Spice plantation tour", "Mandovi river sunset cruise",
                   "Butterfly Beach boat trip", "Divar Island ferry ride"],
        "food": ["Goan fish curry rice", "bebinca dessert", "beach-shack seafood", "veg thali at Ritz Classic",
                 "xacuti at a Panjim café", "sunset dinner at Thalassa"],
        "train": "Madgaon (MAO) / Thivim (THVM) railway stations; Vande Bharat from Mumbai in ~8 hrs.",
        "local": "Rent a scooter (₹400-600/day) or use GoaMiles taxis.",
    },
    "jaipur": {
        "state": "Rajasthan", "area": "near MI Road / C-Scheme, close to the Old City (Pink City)",
        "season": "October-March is pleasant; April-June is very hot (40°C+).",
        "hotels": [("Rambagh Palace (Taj)", "Bhawani Singh Rd", "₹35,000+", 4.8),
                   ("Alsisar Haveli", "Old City", "₹7,000-10,000", 4.5),
                   ("ITC Rajputana", "Station Road", "₹9,000-14,000", 4.5),
                   ("Zostel Jaipur", "Pink City", "₹800-2,500", 4.4)],
        "sights": ["Amber Fort", "Hawa Mahal", "City Palace", "Jantar Mantar", "Nahargarh Fort sunset",
                   "Jal Mahal", "Albert Hall Museum", "Johari & Bapu Bazaar shopping", "Panna Meena ka Kund",
                   "Chokhi Dhani cultural village", "Galta Ji (Monkey Temple)", "Patrika Gate"],
        "food": ["dal baati churma at Chokhi Dhani", "pyaaz kachori at Rawat Mishthan Bhandar",
                 "lassi at Lassiwala, MI Road", "Rajasthani thali at Suvarna Mahal", "kulfi at Pandit Kulfi",
                 "ghewar at LMB"],
        "train": "Jaipur Junction (JP); Shatabdi / Vande Bharat from Delhi in ~4.5 hrs.",
        "local": "Use Ola/Uber or hire a car with driver for forts (~₹2,500/day). Buy the composite monument ticket.",
    },
    "manali": {
        "state": "Himachal Pradesh", "area": "Old Manali for cafés or near Mall Road for convenience",
        "season": "March-June for pleasant weather; December-February for snow. Rohtang Pass needs an online permit.",
        "hotels": [("The Himalayan", "Hadimba Road", "₹12,000-18,000", 4.6),
                   ("Span Resort & Spa", "Kullu-Manali Highway", "₹9,000-15,000", 4.5),
                   ("Johnson Lodge", "Circuit House Road", "₹4,000-7,000", 4.3),
                   ("Zostel Manali", "Old Manali", "₹700-2,000", 4.4)],
        "sights": ["Hadimba Devi Temple", "Old Manali & Manu Temple", "Solang Valley (paragliding)",
                   "Atal Tunnel & Sissu", "Rohtang Pass (permit)", "Vashisht hot springs", "Jogini Falls trek",
                   "Mall Road", "Naggar Castle", "Kasol & Manikaran day trip", "Beas river rafting (Kullu)",
                   "Tibetan monastery"],
        "food": ["trout at Johnson's Café", "siddu at a local dhaba", "Israeli food in Old Manali",
                 "momos & thukpa on Mall Road", "apple pie at Café 1947", "Himachali dham"],
        "train": "No railhead nearby; overnight Volvo bus from Delhi (~12 hrs, ₹1,200-2,000). Nearest airport Bhuntar (KUU), 50 km.",
        "local": "Hire a local taxi for Solang/Atal Tunnel (~₹3,000/day); roads can close after snowfall.",
    },
    "kerala": {
        "state": "Kerala", "area": "Fort Kochi, then Munnar hills and an Alleppey houseboat",
        "season": "September-March is ideal; June-August is monsoon (great for Ayurveda, fewer tourists).",
        "hotels": [("Brunton Boatyard (CGH Earth)", "Fort Kochi", "₹14,000-20,000", 4.7),
                   ("Blanket Hotel & Spa", "Munnar", "₹9,000-14,000", 4.5),
                   ("Premium houseboat (1 night, meals incl.)", "Alleppey backwaters", "₹9,000-15,000", 4.4),
                   ("Zostel Fort Kochi", "Fort Kochi", "₹800-2,000", 4.3)],
        "sights": ["Fort Kochi & Chinese fishing nets", "Mattancherry Palace & Jew Town", "Kathakali show",
                   "Drive to Munnar via Cheeyappara waterfalls", "Tea Museum & tea estates, Munnar",
                   "Eravikulam National Park", "Mattupetty Dam & Echo Point", "Alleppey houseboat cruise",
                   "Marari Beach", "Kumarakom bird sanctuary", "Ayurvedic massage", "Village canoe tour"],
        "food": ["Kerala sadya on a banana leaf", "appam & stew", "karimeen pollichathu",
                 "puttu & kadala curry", "Malabar parotta", "filter coffee & banana chips"],
        "train": "Ernakulam Junction (ERS); Kerala/Rajdhani express from Delhi or Mumbai.",
        "local": "Hire a car with driver for Kochi-Munnar-Alleppey (~₹3,000/day).",
    },
    "varanasi": {
        "state": "Uttar Pradesh", "area": "near Dashashwamedh / Assi Ghat",
        "season": "October-March is best; Dev Deepawali (Nov) is spectacular. Summers are very hot.",
        "hotels": [("BrijRama Palace", "Darbhanga Ghat", "₹18,000-28,000", 4.7),
                   ("Hotel Ganges Grand", "Assi Ghat", "₹4,000-6,000", 4.3),
                   ("Taj Ganges", "Nadesar", "₹9,000-13,000", 4.5),
                   ("Moustache Hostel", "Assi Ghat", "₹600-1,800", 4.4)],
        "sights": ["Sunrise boat ride on the Ganga", "Kashi Vishwanath Temple corridor",
                   "Ganga Aarti at Dashashwamedh Ghat", "Assi Ghat morning aarti", "Sarnath",
                   "Manikarnika Ghat (from a respectful distance)", "BHU & Bharat Kala Bhavan",
                   "Ramnagar Fort", "Old city lanes walk", "Banarasi silk weaving workshop",
                   "Tulsi Manas Temple", "Kaal Bhairav Temple"],
        "food": ["kachori-sabzi breakfast", "Banarasi paan", "lassi at Blue Lassi", "malaiyyo (winter)",
                 "tamatar chaat at Kashi Chaat Bhandar", "thandai"],
        "train": "Varanasi Junction (BSB); Vande Bharat from Delhi in ~8 hrs.",
        "local": "Walk the ghats; use e-rickshaws in the old city. Book temple Sugam Darshan online.",
    },
    "udaipur": {
        "state": "Rajasthan", "area": "around Lake Pichola / Lal Ghat",
        "season": "September-March; post-monsoon the lakes are full.",
        "hotels": [("Taj Lake Palace", "Lake Pichola", "₹45,000+", 4.8),
                   ("Jagat Niwas Palace", "Lal Ghat", "₹6,000-9,000", 4.4),
                   ("Trident Udaipur", "Haridasji ki Magri", "₹10,000-15,000", 4.6),
                   ("Zostel Udaipur", "Lal Ghat", "₹700-2,000", 4.4)],
        "sights": ["City Palace", "Lake Pichola boat ride", "Jag Mandir", "Bagore ki Haveli dance show",
                   "Saheliyon ki Bari", "Fateh Sagar Lake", "Sajjangarh (Monsoon) Palace sunset",
                   "Jagdish Temple", "Ambrai Ghat evening", "Kumbhalgarh Fort day trip", "Vintage car museum",
                   "Shilpgram crafts village"],
        "food": ["dal baati at Natraj", "rooftop dinner at Ambrai", "mirchi vada", "Rajasthani thali",
                 "kachori at Jaiswal", "rabri"],
        "train": "Udaipur City (UDZ); Vande Bharat from Jaipur in ~6.5 hrs.",
        "local": "Autos and boats around the lakes; hire a car for Kumbhalgarh (~₹3,000).",
    },
}
CITY_DATA.update({k: CITY_DATA["kerala"] for k in ["munnar", "kochi", "cochin", "alleppey", "alappuzha"]})
CITY_DATA.update({"north goa": CITY_DATA["goa"], "south goa": CITY_DATA["goa"]})

GENERIC = {
    "state": "", "area": "the main market / old town area",
    "season": "October-March suits most of India; check monsoon timings for your dates.",
    "hotels": [("Heritage Boutique Stay", "Old Town", "₹5,000-8,000", 4.4),
               ("Business Hotel (Lemon Tree / Ginger)", "City Centre", "₹3,000-5,000", 4.2),
               ("Zostel / backpacker hostel", "Market area", "₹700-2,000", 4.3),
               ("Taj / ITC / Oberoi property", "Prime location", "₹12,000+", 4.6)],
    "sights": ["Main temple / heritage site", "Old city walk", "Local bazaar", "State museum",
               "Sunset viewpoint", "Lake or riverfront", "Nearby fort or palace", "Day trip to a nature spot",
               "Local craft village", "Cooking class", "Evening cultural show", "Street-food walk"],
    "food": ["local thali", "street-food chaat walk", "regional speciality dinner", "dhaba lunch",
             "café hopping", "famous local sweet shop"],
    "train": "Check IRCTC for Vande Bharat / Rajdhani / Shatabdi options.",
    "local": "Use Ola/Uber/Rapido or hire a car with driver for day trips.",
}

_BUDGETS = ["luxury", "budget", "mid-range", "mid range", "cheap", "backpacker", "premium"]
_INTERESTS = ["food", "temples", "heritage", "history", "beaches", "nightlife", "shopping", "trekking",
              "hiking", "nature", "wildlife", "adventure", "culture", "photography", "relaxation", "spiritual"]
_PREFS = {"vegetarian": "vegetarian", "vegan": "vegan", "jain": "Jain food", "window seat": "prefers window seat",
          "4-star": "prefers 4-star hotels", "5-star": "prefers 5-star hotels", "wheelchair": "needs wheelchair access",
          "slow pace": "prefers a relaxed pace", "relaxed": "prefers a relaxed pace", "train": "open to train travel",
          "non-stop": "prefers non-stop flights"}
_WORDS = r"([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)"


def city(trip: dict) -> dict:
    return CITY_DATA.get((trip.get("destination") or "").lower(), GENERIC)


def parse_request(query: str, previous: dict | None) -> TripDetails:
    previous = previous or {}
    q = query.lower()
    _skip = {"new_preferences", "clarification_question"}  # transient fields, never carried into a follow-up
    data = {k: v for k, v in previous.items() if k in TripDetails.model_fields and k not in _skip}

    places = find_places(query)
    origin_pos = None
    if m := re.search(r"\bfrom\s+", q):
        after = [p for p in places if p[0] == m.end()]
        if after:
            origin_pos, data["origin"] = after[0][0], after[0][1].title()
        elif m2 := re.search(r"\bfrom\s+" + _WORDS, query):
            data["origin"] = m2.group(1)
        data["origin_iata"] = None
    dests = [p for p in places if p[0] != origin_pos]
    if dests:
        data["destination"], data["destination_iata"] = dests[0][1].title(), None
    elif m := re.search(r"\b(?:to|in|visit|visiting)\s+" + _WORDS, query):
        data["destination"], data["destination_iata"] = m.group(1), None

    if m := re.search(r"(\d+)\s*(?:-\s*)?(?:days?|nights?)", q):
        data["num_days"] = int(m.group(1))
        data.pop("end_date", None)
    elif "weekend" in q:
        data["num_days"] = 2
    if m := re.search(r"(\d+)\s*(?:people|persons|travell?ers|adults|friends|of us)", q):
        data["travelers"] = int(m.group(1))
    elif "couple" in q or "my wife" in q or "my husband" in q or "honeymoon" in q:
        data["travelers"] = 2
    elif "family" in q and not data.get("travelers"):
        data["travelers"] = 4
    for b in _BUDGETS:
        if b in q:
            data["budget"] = b
    if m := re.search(r"(\d{4}-\d{2}-\d{2})", q):
        data["start_date"] = m.group(1)
    elif not data.get("start_date"):
        data["start_date"] = (date.today() + timedelta(days=30)).isoformat()
    if found := [i for i in _INTERESTS if i in q]:
        data["interests"] = found
    prefs = [v for k, v in _PREFS.items() if re.search(r"\b" + re.escape(k) + r"\b", q)]
    if not data.get("destination"):
        return TripDetails(**data, clarification_question="Where in India would you like to travel, and for how many days?")
    return TripDetails(**data, new_preferences=prefs)


def _delay():
    time.sleep(AGENT_DELAY_SECONDS)


def weather(trip: dict) -> str:
    """Live Open-Meteo forecast even in demo mode (it's free and needs no key)."""
    _delay()
    from travel_agent.india import region_hint
    from travel_agent.tools.weather import get_weather

    data = get_weather(trip["destination"], trip.get("start_date"), min(trip.get("num_days") or 5, 7),
                       region=region_hint(trip["destination"]))
    return f"### Weather & packing: {trip['destination']}\n\n{data}\n\n_Live data from Open-Meteo (free)._"


def budget(state: dict) -> str:
    _delay()
    trip = state["trip"]
    days, people = trip.get("num_days") or 3, trip.get("travelers") or 1
    luxury = (trip.get("budget") or "") in {"luxury", "premium"}
    budget_lvl = (trip.get("budget") or "") in {"budget", "cheap", "backpacker"}
    hotel_night = 18000 if luxury else 2000 if budget_lvl else 6000
    per_day = 3000 if luxury else 900 if budget_lvl else 1800
    travel_pp = 11000 if trip.get("origin") else 0
    food, act, local = per_day * days, per_day * days // 2, 600 * days
    rooms = max(1, (people + 1) // 2)
    buffer = 2000 * people
    total = (travel_pp + food + act + local) * people + hotel_night * days * rooms + buffer
    tips = {
        True: "Travel midweek, book trains in advance, and eat at local thali places to save.",
        False: "",
    }
    lvl = trip.get("budget") or "mid-range"
    return f"""### Budget estimate ({lvl}) - {days} days, {people} traveller(s)

| Item | Estimate (INR) |
|---|---|
| Flights / trains (return, {people} pax) | ₹{travel_pp * people:,} |
| Hotel ({days} nights, {rooms} room) | ₹{hotel_night * days * rooms:,} |
| Food | ₹{food * people:,} |
| Activities & entry | ₹{act * people:,} |
| Local transport | ₹{local * people:,} |
| Buffer | ₹{buffer:,} |
| **Total** | **₹{total:,}** |

**Money-saving tips:** Travel midweek and book IRCTC trains early; eat at local thali spots; use UPI to skip ATM fees.

_Demo estimate - figures are approximate._"""


def _iata_note(trip: dict) -> str:
    dest = (trip.get("destination") or "").lower()
    code = trip.get("destination_iata")
    if code and dest in INDIA_PLACES and dest not in {"delhi", "mumbai", "goa", "jaipur", "udaipur", "varanasi"}:
        return f"\n> {trip['destination']} is served by the nearest airport **{code}**; continue by road or train.\n"
    return ""


def flights(trip: dict) -> str:
    _delay()
    o, d, c = trip.get("origin"), trip["destination"], city(trip)
    oi, di = trip.get("origin_iata") or o, trip.get("destination_iata") or d
    return f"""### Best options: {o} ({oi}) → {d} ({di})
{_iata_note(trip)}
| Option | Carrier | Stops | Duration | Approx. fare (per person) |
|---|---|---|---|---|
| Cheapest | IndiGo / Akasa Air | Non-stop | ~2h 15m | ₹4,500-6,500 |
| Most flexible | Air India | Non-stop | ~2h 20m | ₹6,500-9,000 |
| Best value | IndiGo (early morning) | Non-stop | ~2h 10m | ₹4,000-5,500 |

**🚆 Train / bus alternative:** {c['train']}

**Booking tips**
- Book 3-4 weeks ahead; avoid long weekends and festival dates (Diwali, Christmas, New Year).
- Early-morning and late-night flights are usually cheapest; set fare alerts on Google Flights.
- For trains, book on IRCTC up to 60 days ahead; try Tatkal one day before if needed.

_Demo data: add AVIATIONSTACK_API_KEY and TAVILY_API_KEY for live schedules and fares._"""


def hotels(trip: dict) -> str:
    _delay()
    c = city(trip)
    rows = "\n".join(f"| {n} | {a} | {p} | ⭐ {r} |" for n, a, p, r in c["hotels"])
    return f"""### Hotel comparison: {trip['destination']}

| Hotel | Area | Price / night | Rating |
|---|---|---|---|
{rows}

**Where to stay:** {c['area']}.

_Demo data: add TAVILY_API_KEY / GOOGLE_MAPS_API_KEY for live hotel results._"""


def itinerary(trip: dict) -> str:
    _delay()
    c, days = city(trip), trip.get("num_days") or 3
    sights, food = c["sights"], c["food"]
    out = [f"### {days}-day itinerary: {trip['destination']}"]
    for i in range(days):
        s = [sights[(i * 3 + k) % len(sights)] for k in range(3)]
        title = " - Arrival & easy start" if i == 0 else (" - Departure" if i == days - 1 and days > 1 else "")
        out.append(f"""
#### Day {i + 1}{title}
- **Morning:** {s[0]}
- **Afternoon:** {s[1]}
- **Evening:** {s[2]}, then dinner: {food[i % len(food)]}""")
    return "\n".join(out)


def final(state: dict) -> str:
    _delay()
    trip, c = state["trip"], city(state["trip"])
    days, people = trip.get("num_days") or 3, trip.get("travelers") or 1
    prefs = state.get("preferences") or []
    pref_line = f"\n> Personalised for your saved preferences: **{', '.join(prefs)}**\n" if prefs else ""
    overview = (f"A {days}-day trip" + (f" from {trip['origin']}" if trip.get("origin") else "") +
                f" for {people} traveler(s), starting {trip.get('start_date') or 'on flexible dates'}" +
                (f", {trip['budget']} budget" if trip.get("budget") else "") +
                (". Focus: " + ", ".join(trip["interests"]) if trip.get("interests") else "") + ".")

    # Only include sections for the agents the supervisor actually selected.
    blocks = [f"## 🇮🇳 Your trip to {trip['destination']}"
              f"{', ' + c['state'] if c['state'] and c['state'].lower() != trip['destination'].lower() else ''}",
              f"### Trip Overview\n{overview}\n{pref_line}"]
    labelled = [("Flights & Trains", state.get("flight_results")), ("Where to Stay", state.get("hotel_results")),
                ("Weather & Packing", state.get("weather_info")), ("Day-by-Day Itinerary", _strip_heading(state.get("itinerary"))),
                ("Estimated Budget", state.get("budget_analysis"))]
    for label, text in labelled:
        if text:
            blocks.append(f"### {label}\n{text}")
    blocks.append(
        "### Practical Tips\n"
        f"- **Best season:** {c['season']}\n- **Getting around:** {c['local']}\n"
        "- Carry some cash for small vendors; UPI works almost everywhere.\n"
        "- Keep a digital copy of your ID (Aadhaar/DigiLocker) for hotel check-in."
    )
    blocks.append("---\n_🧪 Demo mode: sample data shown. Start Ollama or add a free GROQ_API_KEY for live AI planning._")
    return "\n\n".join(blocks)


def _strip_heading(text: str | None) -> str:
    return text.split("\n", 1)[-1] if text else ""
