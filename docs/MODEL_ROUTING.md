# Model routing

LayoffLens AI supports `simulation`, `hybrid`, and `live` execution modes.

- `simulation`: deterministic planning and local registered tools; no model or external network calls.
- `live`: the supervisor requests a structured plan from the configured Meta Responses provider. Each selected specialist receives its own role-specific prompt and model call. Model-produced handoffs can enqueue additional allow-listed agents, and the supervisor can request a bounded re-plan after unresolved findings.
- `hybrid`: uses configured model calls where enabled and retains deterministic analytical tools for authoritative calculations. Provider availability and fallback behavior must be recorded rather than silently represented as model success.

Set `WRI_AGENT_MODE=live` and `MODEL_API_KEY` only when authorized to make real provider requests. The default model identifier is configured by `META_MODEL_ID`. Optional role-specific identifiers are supported through `META_SUPERVISOR_MODEL`, `META_SIGNAL_MODEL`, `META_RESEARCH_MODEL`, `META_FINANCE_MODEL`, `META_DEMAND_MODEL`, `META_CAPACITY_MODEL`, `META_OPERATIONS_MODEL`, `META_SCENARIO_MODEL`, `META_ALTERNATIVES_MODEL`, `META_REVIEW_MODEL`, and `META_REPORTING_MODEL`. They must be valid identifiers supported by the configured Meta API account; this project does not assert that every model supports every capability.

The current provider adapter is Meta-specific. Different role-specific model IDs can be selected within that provider; additional provider implementations are future work. The current live path is contract/mock-tested but has not been called against a live API. Models do not calculate authoritative financial values or independently retrieve the internet.

`GET /api/providers/status` reports `demo_no_network`,
`configured_not_tested`, or `missing_credentials` states without returning
keys. No live request is made automatically; live verification requires explicit
authorization and approved provider credits.

All model-generated plans and handoffs are checked against registered agents, registered tools, declared dependencies, permissions, and execution budgets. Deterministic calculations remain authoritative.
