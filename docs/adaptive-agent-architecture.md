# Adaptive agent architecture

LayoffLens AI uses a bounded hybrid workflow rather than an autonomous enterprise agent.

1. The synthetic source records are validated by the data-quality manager.
2. An event type selects a deterministic investigation policy:
   - `project_delay` starts with project demand, then capacity and scenarios.
   - `infrastructure_cost` starts with finance, then scenarios and interventions.
3. Each permitted specialist returns a typed `AgentResult` with status, evidence IDs,
   selection reason, and upstream inputs.
4. Dependent specialists receive the completed upstream result in their structured
   input. The evidence reviewer checks every cited ID against the source inventory.
5. A bounded budget stops execution. Failed or unsupported steps mark the run as
   degraded and require human review.
6. The optional Meta adapter only synthesizes validated results. Demo mode is
   deterministic and makes no network requests; live inference remains unverified.

The adapter also exposes a strict validator for a structured model tool request.
Mocked requests can be tested locally, but the default demo policy does not ask a
model to select tools and therefore remains deterministic.

No employee-level scores, termination recommendations, arbitrary tool execution, or
continuous learning are implemented. Enterprise connectors, identity, and production
governance remain roadmap items.
