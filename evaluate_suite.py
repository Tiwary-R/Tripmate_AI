"""Offline evaluation suite - scores TripMate AI on a set of sample trips and prints an aggregate.

Runs each case through the planner and scores it with travel_agent.evaluation.evaluate().
Defaults to DEMO_MODE (fast, deterministic, no model). For a live run with the LLM judge:

    # Windows PowerShell
    $env:DEMO_MODE=""; python evaluate_suite.py --live

Usage:
    python evaluate_suite.py              # demo mode, heuristic metrics
    python evaluate_suite.py --live       # use the configured LLM (slower) + LLM judge
"""

import argparse
import os
import sys
import uuid

CASES = [
    {"name": "Goa (India, budget)", "query": "4 days in Goa from Bengaluru for 4 friends on a budget, beaches"},
    {"name": "Jaipur (India, luxury)", "query": "5 day trip to Jaipur from Delhi for a couple, luxury, heritage. We are vegetarian."},
    {"name": "Paris (international)", "query": "5 days in Paris from Mumbai, mid-range, museums and food"},
    {"name": "Tokyo (international)", "query": "7 day trip to Tokyo from Delhi, food and culture"},
    {"name": "Weather-only (no origin)", "query": "What's the weather like in Rome and a 3 day plan, history"},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="use the configured LLM instead of demo mode")
    args = parser.parse_args()
    if not args.live:
        os.environ["DEMO_MODE"] = "true"

    from travel_agent.evaluation import evaluate
    from travel_agent.orchestrator import TravelPlanner

    planner = TravelPlanner()
    print(f"Running {len(CASES)} cases ({'LIVE' if args.live else 'DEMO'})...\n")
    rows, total = [], 0
    for case in CASES:
        thread = f"eval-{uuid.uuid4().hex[:8]}"
        for _node, _upd in planner.stream(case["query"], thread, "evaluator", hitl=False):
            pass
        state = planner.get_values(thread)
        report = state.get("eval_report") or evaluate(state)
        score = report.get("overall", 0)
        total += score
        rows.append((case["name"], score, report.get("grade", "-"),
                     "; ".join(report.get("notes", [])[:2]) or "all good"))

    width = max(len(r[0]) for r in rows)
    print(f"{'Case'.ljust(width)}  Score  Grade  Notes")
    print("-" * (width + 30))
    for name, score, grade, notes in rows:
        print(f"{name.ljust(width)}  {str(score).rjust(5)}  {grade.center(5)}  {notes}")
    print("-" * (width + 30))
    avg = round(total / len(rows)) if rows else 0
    print(f"{'AGGREGATE'.ljust(width)}  {str(avg).rjust(5)}")
    sys.exit(0 if avg >= 60 else 1)  # non-zero exit if the suite average is weak (useful in CI)


if __name__ == "__main__":
    main()
