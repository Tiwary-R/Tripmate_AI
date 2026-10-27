from travel_agent import demo


def test_parse_request_extracts_fields():
    d = demo.parse_request("4 days in Goa from Pune on a budget, beaches", None)
    assert d.destination and d.destination.lower() == "goa"
    assert d.origin and d.origin.lower() == "pune"
    assert d.num_days == 4
    assert d.budget == "budget"


def test_parse_request_followup_keeps_previous():
    first = demo.parse_request("5 days in Jaipur from Delhi", None)
    follow = demo.parse_request("make it 7 days", first.model_dump())
    assert follow.destination.lower() == "jaipur"
    assert follow.num_days == 7


def test_parse_request_missing_destination_asks():
    d = demo.parse_request("I want to go on a holiday", None)
    assert d.clarification_question
