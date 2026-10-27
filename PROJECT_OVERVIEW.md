# TripMate AI — Project Overview

### A multi-agent, Responsible-AI travel planner for worldwide trips

**Prepared for:** Management review
**Prepared by:** r.a.tiwary

---

## 1. Executive summary

TripMate AI takes a traveller's request in plain English — for example *"Plan 5 days in Jaipur from Delhi,
heritage and food, mid-range budget"* — and produces a complete, practical travel plan: flights or trains,
hotels, weather and packing advice, a day-by-day itinerary, and an estimated budget.

Instead of one large AI doing everything, the work is split across **a team of specialised AI agents**, each
an expert in one area, coordinated automatically. Safety and **Responsible AI** controls are applied at
every step — not as an afterthought.

The entire system runs on **free, open tools and models** (a local Llama model and free public APIs), so
there is **no per-query cost** and user data can stay on-premise.

---

## 2. How many agents, and what each one does

The system uses **7 AI agents** plus **2 control gates**.

### The 7 AI agents

| # | Agent | Purpose | Data / tools it uses |
|---|---|---|---|
| 1 | **Supervisor Agent** | The "brain". Understands the request, extracts the trip details (cities, dates, budget, travellers), and **decides which specialist agents are actually needed** for this trip. No fixed script. | The LLM |
| 2 | **Flight Agent** | Finds the best flights and trains, compares cost/time, gives booking tips. | AviationStack (schedules) + web search, via MCP |
| 3 | **Hotel Agent** | Recommends and compares hotels across budget levels and suggests the best area to stay. | Web search + Google Places, via MCP |
| 4 | **Weather Agent** | Gives a weather outlook and a packing list tailored to the destination and season. | Open-Meteo (free weather API), via MCP |
| 5 | **Budget Agent** | Produces an itemised cost estimate in INR and money-saving tips. | The LLM + the other agents' findings |
| 6 | **Itinerary Agent** | Builds a realistic day-by-day plan of places and activities, grouped to reduce travel. | Web search + Google Places + the weather outlook |
| 7 | **Final Response Agent** | Combines all the specialist reports into one clean, readable travel plan. | The LLM |

### The 2 control gates (not LLM "experts", but essential steps)

| Gate | Purpose |
|---|---|
| **Input Guardrail** | The security checkpoint at the entrance — validates every request before any work starts. |
| **Human-in-the-Loop** | Optional pause for a person to review and approve the plan before the agents run. |

**Why a team instead of one AI?** Each agent has a focused job and the right tool, which makes results more
accurate and easier to trust, debug and improve. The Supervisor only runs the agents a given trip needs
(e.g. a weekend trip with no origin city skips the Flight Agent), which saves time and compute.

---

## 3. The workflow, step by step — and where guardrails & Responsible AI apply

```
STEP 1   User request
            |
            v
STEP 2   INPUT GUARDRAIL        <-- Guardrail + Responsible AI (safety, injection, scope)
            |  (pass)                If blocked: stop with a clear reason.
            v
STEP 3   SUPERVISOR AGENT        <-- Scope check (worldwide; optional India-only)
            |                        Decides which specialists to run.
            v
STEP 4   HUMAN REVIEW (optional) <-- Human oversight: approve / cancel / adjust
            |  (approved)
            v
STEP 5   SPECIALIST AGENTS       <-- Responsible AI guard on EVERY agent's output
         (Flight, Hotel, Weather,    (PII redaction, safety scan, disclaimers)
          Budget, Itinerary — run
          in parallel)
            |
            v
STEP 6   FINAL RESPONSE AGENT    <-- Responsible AI (final safety pass + PII redaction)
            |
            v
STEP 7   Plan shown to the user  +  a Responsible-AI report of every check that ran
```

**Key point for review:** a guardrail runs at the entrance (Step 2), the scope policy is enforced at the
Supervisor (Step 3), a human can approve (Step 4), and a Responsible-AI guard wraps **every single agent**
(Steps 5–6). Safety is layered through the whole pipeline, not bolted on at one point.

---

## 4. Guardrails — where and what

Guardrails are applied in **two layers**, so nothing unsafe gets in and nothing unsafe gets out.

### Layer 1 — Input Guardrail (Step 2, at the entrance)
Checks every request before any processing:
- **Relevance** — is this actually a travel request? Irrelevant messages are declined.
- **Safety** — blocks unsafe, harmful or illegal requests.
- **Prompt-injection / jailbreak defense** — detects attempts like *"ignore your instructions"* and blocks them.
- **Validity** — empty or nonsensical input is rejected with guidance.

If a request fails, the system **stops and explains why**, rather than guessing.

### Layer 2 — Policy Guardrail (Step 3, at the Supervisor)
- **Scope policy: worldwide (configurable).** Trips to any country are supported; an optional India-only mode politely
  declined and domestic alternatives are suggested.

### Output guardrail on every agent (Steps 5–6)
Every specialist agent and the final response pass through an output guardrail (see Responsible AI below).

---

## 5. Responsible AI — the four pillars and where each is used

Responsible AI is built into the system, applied at the steps shown.

| Pillar | What it does | Where it runs |
|---|---|---|
| **Safety / content moderation** | Screens content against safety categories using **Llama Guard** (a free, industry-standard safety model from Meta), with a fast rule-based scan as backup. | Input (Step 2) and final output (Step 6); rule scan on every agent (Step 5) |
| **Privacy / PII protection** | Automatically detects and redacts personal data — email, phone, Aadhaar, PAN, card numbers — so it is never shown or stored. Prices and dates are kept. | Every agent's output (Steps 5–6) and the stored chat history |
| **Prompt-injection defense** | Detects and blocks jailbreak / instruction-override attempts. | Input (Step 2) |
| **Transparency & fairness** | A visible "Responsible AI" report shows every check that ran; agents are instructed to be inclusive and non-discriminatory; plans carry a "figures are estimates" disclaimer so users aren't misled. | Every agent (prompt-level) + a transparency panel in the UI |

**Efficient by design:** the per-agent privacy/safety checks are instant rule-based scans (no extra AI
calls). The heavier Llama Guard model runs only at the two ends (entrance and final answer), so safety adds
at most ~2 extra model calls to an entire plan.

**Every check is recorded.** The user (and we) can see, per agent, which engine ran, whether any PII was
redacted, whether injection was detected, and whether a disclaimer was added — full transparency.

---

## 6. Design highlights for management

- **Zero running cost.** Uses a free local LLM (Ollama / Llama 3) or the free Groq tier, and free public
  APIs (Open-Meteo for weather). No paid API is required to operate.
- **Privacy-friendly.** Can run entirely on local infrastructure; PII is redacted automatically; user
  accounts use salted, hashed passwords (never stored in plain text).
- **Resilient.** If an optional data source is unavailable, the affected agent degrades gracefully and the
  plan is still produced — no hard failures.
- **Memory.** Remembers each user's preferences (e.g. "vegetarian", "prefers trains") across conversations.
- **Human oversight.** A human can review and approve the plan before it is generated (configurable).
- **Automated evaluation.** Every plan is scored (0-100 + grade) by heuristic metrics plus an optional LLM-as-judge, shown in the UI.
- **Modern architecture.** Built on **Google ADK** (agent orchestration, sessions, memory) with tools exposed through **MCP**
  (Model Context Protocol), the emerging open standard for connecting AI to tools.

---

## 7. Technology at a glance

| Area | Choice |
|---|---|
| Agent orchestration | Google ADK |
| AI model (LLM) | Llama 3 — local via Ollama (free), or Groq free tier |
| Safety model | Llama Guard (free) |
| Tool protocol | MCP (Model Context Protocol) |
| Weather | Open-Meteo (free, no key) |
| Flights / search / places | AviationStack, Tavily, Google Places (optional) |
| Memory | PostgreSQL (or in-memory) |
| User interface | Streamlit web app (with login) |
| Accounts | SQLite + PBKDF2 password hashing |

---

## 8. Summary — the one-line answers

- **How many agents?** 7 AI agents (1 Supervisor + 5 specialists + 1 Final Response), plus 2 control gates
  (Input Guardrail and Human Review).
- **What is each agent for?** See Section 2 — flights, hotels, weather, budget, itinerary, with a Supervisor
  that routes and a Final agent that assembles the answer.
- **Where are guardrails used?** At the entrance (safety, injection, relevance), at the Supervisor
  (scope policy), and on every agent's output.
- **Where is Responsible AI used?** Safety moderation at the entrance and final output, PII redaction on
  every agent, injection defense at the entrance, and transparency/fairness throughout — with a visible
  report of every check.

---

*TripMate AI — a safe, explainable, cost-free multi-agent travel planner.*
