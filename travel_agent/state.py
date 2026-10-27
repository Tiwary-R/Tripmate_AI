from typing import Optional, TypedDict

from pydantic import BaseModel, Field

SPECIALIST_AGENTS = ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"]


class TripDetails(BaseModel):
    """Structured trip request extracted from the user's message (the supervisor's trip_constraints)."""

    origin: Optional[str] = Field(None, description="Departure city, e.g. 'Mumbai'")
    origin_iata: Optional[str] = Field(None, description="3-letter IATA code of the nearest origin airport")
    origin_country: Optional[str] = Field(None, description="ISO 3166 alpha-2 country code of the origin, e.g. 'IN'")
    destination: Optional[str] = Field(None, description="Destination city or region, e.g. 'Manali'")
    destination_iata: Optional[str] = Field(None, description="3-letter IATA code of the nearest destination airport")
    destination_country: Optional[str] = Field(None, description="ISO 3166 alpha-2 country code of the destination")
    start_date: Optional[str] = Field(None, description="Trip start date, YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="Trip end date, YYYY-MM-DD")
    num_days: Optional[int] = Field(None, description="Number of days of the trip")
    travelers: Optional[int] = Field(None, description="Number of travelers")
    budget: Optional[str] = Field(None, description="Budget, e.g. 'INR 1,00,000' or 'mid-range'")
    interests: list[str] = Field(default_factory=list, description="Interests, e.g. food, museums, hiking")
    new_preferences: list[str] = Field(
        default_factory=list,
        description="Lasting personal preferences the user stated (e.g. 'vegetarian', 'prefers window seat'). Empty if none.",
    )
    clarification_question: Optional[str] = Field(
        None, description="Ask this only if the destination is missing or unclear; otherwise null"
    )


class SupervisorDecision(BaseModel):
    """Which specialist agents to run for this request, and why."""

    selected_agents: list[str] = Field(
        default_factory=list,
        description="Subset of: flight_agent, hotel_agent, weather_agent, budget_agent, itinerary_agent. "
        "Pick only the ones this request needs. Omit flight_agent if no origin is given.",
    )
    reasoning: str = Field("", description="One or two sentences explaining the choice.")


class GuardrailVerdict(BaseModel):
    """Input guardrail decision."""

    allow: bool = Field(..., description="True if the request is a safe, relevant travel-planning request.")
    reason: str = Field("", description="If blocked, a short user-facing reason. Empty if allowed.")
    category: str = Field("ok", description="One of: ok, irrelevant, unsafe, out_of_scope, invalid")


class TravelState(TypedDict, total=False):
    user_id: str
    user_query: str
    # Guardrail
    guardrail_passed: bool
    guardrail_reason: str
    # Supervisor
    trip: dict  # the trip_constraints
    preferences: list[str]
    selected_agents: list[str]
    supervisor_reasoning: str
    # Human-in-the-loop
    hitl_feedback: str
    # Long-term memory recalled for this request
    recalled_memory: str
    # Specialist outputs
    flight_results: str
    hotel_results: str
    weather_info: str
    budget_analysis: str
    itinerary: str
    # Final
    final_response: str
    eval_report: dict  # per-run evaluation score + breakdown
    # Reducers are applied by the orchestrator's merge (sum llm_calls, concat rai_log, append messages).
    llm_calls: int
    rai_log: list  # Responsible-AI transparency events (one per guarded node)
    messages: list
