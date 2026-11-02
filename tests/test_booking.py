from travel_agent import booking


def _india_trip():
    return {
        "origin": "Delhi", "origin_iata": "DEL", "origin_country": "IN",
        "destination": "Goa", "destination_iata": "GOI", "destination_country": "IN",
        "start_date": "2026-11-05", "end_date": "2026-11-10", "num_days": 5, "travelers": 2,
    }


def _intl_trip():
    return {
        "origin": "Mumbai", "origin_iata": "BOM", "origin_country": "IN",
        "destination": "Paris", "destination_iata": "CDG", "destination_country": "FR",
        "start_date": "2026-11-05", "end_date": "2026-11-10", "num_days": 5, "travelers": 2,
    }


def test_india_flight_providers_include_indian_otas():
    names = [p["name"] for p in booking.flight_providers(_india_trip())]
    assert "MakeMyTrip" in names
    urls = " ".join(p["url"] for p in booking.flight_providers(_india_trip()))
    assert "makemytrip.com" in urls
    assert "skyscanner.net/transport/flights/del/goi/" in urls  # lowercased IATA
    assert "261105" in urls  # skyscanner yymmdd departure


def test_intl_flight_providers_are_global():
    names = [p["name"] for p in booking.flight_providers(_intl_trip())]
    assert "Skyscanner" in names and "Kayak" in names
    assert "MakeMyTrip" not in names


def test_intl_hotel_booking_url_prefilled():
    hotels = booking.hotel_providers(_intl_trip())
    bk = next(p for p in hotels if p["name"] == "Booking.com")
    assert "ss=Paris" in bk["url"]
    assert "checkin=2026-11-05" in bk["url"] and "checkout=2026-11-10" in bk["url"]
    # India-only OTAs absent for an international trip
    assert "Goibibo" not in [p["name"] for p in hotels]


def test_india_hotel_providers_include_indian_otas():
    names = [p["name"] for p in booking.hotel_providers(_india_trip())]
    assert "MakeMyTrip" in names and "Goibibo" in names


def test_estimate_from_markdown_range_and_none():
    assert booking.estimate_from_markdown("Cheapest fare ₹4,500-6,500 per person") == "₹4,500–6,500"
    assert booking.estimate_from_markdown("Hotel Rs 2,000/night") == "Rs2,000"
    assert booking.estimate_from_markdown("No prices mentioned here") is None
    assert booking.estimate_from_markdown("") is None


def test_missing_dates_still_build_links():
    trip = {"origin": "Delhi", "origin_iata": "DEL", "destination": "Goa",
            "destination_iata": "GOI", "destination_country": "IN", "travelers": 1}
    flights = booking.flight_providers(trip)
    hotels = booking.hotel_providers(trip)
    assert flights and hotels  # no exception, links present
    bk = next(p for p in hotels if p["name"] == "Booking.com")
    assert "checkin=" not in bk["url"]  # omitted when no dates


def test_destination_with_space_is_encoded():
    trip = {"destination": "New York", "destination_country": "US", "travelers": 1}
    bk = next(p for p in booking.hotel_providers(trip) if p["name"] == "Booking.com")
    assert "New%20York" in bk["url"] or "New+York" in bk["url"]


def test_no_origin_returns_no_flights_but_hotels_ok():
    trip = {"destination": "Goa", "destination_country": "IN", "travelers": 1}
    assert booking.flight_providers(trip) == []
    assert booking.hotel_providers(trip)


def test_booking_markdown_has_section_and_links():
    md = booking.booking_markdown(_india_trip(), "fare ₹4,500-6,500", "Rs 2,000/night")
    assert "## Booking & price comparison" in md
    assert "MakeMyTrip" in md and "](http" in md
    assert "₹4,500–6,500" in md  # flight estimate surfaced
