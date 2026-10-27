from travel_agent.evaluation import evaluate


def _good_state():
    return {
        "guardrail_passed": True,
        "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "itinerary_agent"],
        "trip": {"destination": "Paris", "destination_country": "FR", "num_days": 3},
        "flight_results": "Flights from Mumbai to Paris, approx EUR 500.",
        "hotel_results": "Hotels in Le Marais, EUR 150/night.",
        "weather_info": "Mild, 12-18C. Pack a light jacket.",
        "itinerary": "#### Day 1\nLouvre\n#### Day 2\nMontmartre\n#### Day 3\nVersailles",
        "final_response": "## Paris plan\nFlights EUR 500...\nDay 1 Louvre\nDay 2\nDay 3",
        "rai_log": [{"safety": {"safe": True}, "pii": [], "injection": False}],
        "llm_calls": 5,
    }


def test_evaluate_good_plan_scores_well():
    report = evaluate(_good_state(), latency_s=10, use_judge=False)
    assert report["overall"] >= 70
    assert report["grade"] in {"A", "B", "C"}
    assert any(m["name"] == "Completeness" for m in report["metrics"])


def test_evaluate_blocked_state_low_safety():
    state = {"guardrail_passed": False, "selected_agents": [], "final_response": "blocked",
             "rai_log": [{"safety": {"safe": False, "categories": ["unsafe"]}, "pii": [], "injection": True}]}
    report = evaluate(state, use_judge=False)
    safety = next(m for m in report["metrics"] if m["name"] == "Safety")
    assert safety["score"] == 0
    assert report["judge"] is None
