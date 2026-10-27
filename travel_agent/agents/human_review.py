"""Human-in-the-Loop helpers - pause after the supervisor so the user can review/approve the plan.

The orchestrator (travel_agent/orchestrator.py) drives the pause/resume: it emits `review_payload(state)`
as an interrupt, then applies the user's decision with `apply_decision(decision)`. No LangGraph dependency.
"""

from travel_agent.state import TravelState


def review_payload(state: TravelState) -> dict:
    """The payload shown to the user when the plan pauses for review."""
    return {
        "type": "plan_review",
        "trip": state.get("trip", {}),
        "selected_agents": state.get("selected_agents", []),
        "reasoning": state.get("supervisor_reasoning", ""),
        "question": "Review the plan. Approve to continue, or add a note to adjust it.",
    }


def apply_decision(decision: dict | None) -> dict:
    """Turn the user's review decision into a state update.

    approve  -> {} (or a note saved to hitl_feedback)
    cancel   -> clear selected_agents and set a cancellation message
    """
    action = (decision or {}).get("action", "approve")
    note = (decision or {}).get("note", "").strip()
    if action == "cancel":
        return {
            "selected_agents": [],
            "final_response": "👍 Okay, I've stopped here. Tell me what you'd like to change and we'll re-plan.",
        }
    return {"hitl_feedback": note} if note else {}
