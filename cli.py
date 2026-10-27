"""Terminal chat for the travel planner.

Run:  python cli.py [--thread THREAD_ID] [--user USER_ID]
"""

import argparse
import uuid

from travel_agent.orchestrator import TravelPlanner
from travel_agent.memory import close_memory

LABELS = {
    "planner": "Planner parsed the request",
    "flight_agent": "Flight Agent done",
    "hotel_agent": "Hotel Agent done",
    "itinerary_agent": "Itinerary Agent done",
    "final_agent": "Final Response Agent done",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread", default=str(uuid.uuid4()), help="conversation id (reuse to continue)")
    parser.add_argument("--user", default="default", help="user id for saved preferences")
    args = parser.parse_args()

    planner = TravelPlanner()
    print(f"TripMate AI  |  memory: {planner.backend}  |  thread: {args.thread}")
    print("Describe your trip (e.g. '5 days in Paris from Delhi in December, mid budget'). Type 'exit' to quit.\n")

    try:
        while True:
            query = input("You: ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            if not query:
                continue
            for node, update in planner.stream(query, args.thread, args.user):
                print(f"  [ok] {LABELS.get(node, node)}")
                if node == "planner" and update:
                    trip = update.get("trip", {})
                    print(f"       {trip.get('origin')} -> {trip.get('destination')}, {trip.get('num_days')} days")
            state = planner.graph.get_state({"configurable": {"thread_id": args.thread}}).values
            print(f"\nTripMate:\n{state.get('final_response', '')}\n")
    finally:
        close_memory()


if __name__ == "__main__":
    main()
