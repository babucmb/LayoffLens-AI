# Agent architecture transformation

## Current architecture

LayoffLens AI uses a bounded hybrid multi-agent runtime connected to the normal investigation entry point.

The supervisor has two planning modes:
- Deterministic policy planning for the no-network demo.
- Structured model-driven planning in live/hybrid mode.

Ten agent roles have separate prompts, objectives, model roles, authorized tool declarations, and structured result contracts. The selected agents each receive a model call in live mode. They may request allow-listed agent handoffs. The supervisor can ask for additional work after unresolved findings or handoffs, subject to budgets and dependency validation.

The existing deterministic specialist calculations remain registered application tools. They are authoritative for numeric analysis; the models interpret findings and coordinate work rather than inventing financial results.

## Important boundaries

- Simulation mode is not presented as live model reasoning.
- Live Meta inference is mock-tested but not live-verified.
- Tavily public research retrieval is implemented but not live-verified.
- Infrastructure intelligence currently analyzes supplied snapshot data, not live cloud telemetry.
- Enterprise SaaS integrations and distributed production orchestration remain future work.

See `AGENT_RUNTIME_IMPLEMENTATION_REPORT.md` and `FINAL_READINESS_REPORT.md` for verification details.
