from travel_agent import india


def test_resolve_airport_curated_india():
    assert india.resolve_airport("Goa") == "GOI"
    assert india.resolve_airport("Manali") == "KUU"


def test_resolve_airport_worldwide():
    cdg = india.resolve_airport("Paris", "CDG")
    assert cdg == "CDG"
    # resolved international airport is in France
    assert india.country_for_iata(cdg) == "FR"


def test_country_for_iata():
    assert india.country_for_iata("GOI") == "IN"
    assert india.country_for_iata("NRT") == "JP"
    assert india.country_for_iata(None) is None


def test_out_of_scope_global(monkeypatch):
    monkeypatch.setattr("travel_agent.config.TRAVEL_SCOPE", "global")
    assert india.out_of_scope("Paris", "FR") is False
    assert india.out_of_scope("Goa", "IN") is False


def test_out_of_scope_india(monkeypatch):
    monkeypatch.setattr("travel_agent.config.TRAVEL_SCOPE", "india")
    assert india.out_of_scope("Paris", "FR") is True
    assert india.out_of_scope("Goa", "IN") is False
