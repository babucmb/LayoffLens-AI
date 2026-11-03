# Agent execution flow

## Runtime modes

The investigation entry point calls `run_investigation`, which constructs a per-investigation runtime and supervisor. Demo mode uses the deterministic planner and performs no model or external research calls. Live mode uses the configured Meta provider for a structured supervisor plan and a separate model call for each selected specialist.

## Live flow

1. The supervisor receives the event type, evidence identifiers, budget, and registered tool catalogue.
2. It requests a structured list of tasks from the supervisor model.
3. The application validates agent/tool names, duplicates, dependencies, mandatory evidence review, and budget.
4. Each selected specialist receives its dedicated prompt, objective, evidence references, authorized tools, and observations.
5. The specialist returns a structured finding and may request an allow-listed handoff to another specialist.
6. The supervisor may re-plan after a handoff or unresolved question.
7. The selected registered tool is invoked through the permission-checked tool registry. Existing deterministic analytical functions remain authoritative for numeric outputs.
8. Evidence review is required before executive reporting.
9. Execution traces include model invocation status, role, findings, tool execution, handoffs, and supervisor replanning events.

The runtime is bounded by `WRI_AGENT_MAX_STEPS`, investigation budget, provider timeout, and the tool/agent allow-lists.

## Registered agents

The ten registered roles are business signal, external research, finance, project demand, workforce capacity, infrastructure operations, scenario, preventive alternatives, evidence/policy review, and executive reporting. The external research role uses the optional Tavily adapter; without credentials it explicitly reports unavailable research. Infrastructure analysis currently operates on supplied snapshot data, not live cloud telemetry.

## Important boundary

Mocked provider tests verify the structured model interaction contract and end-to-end orchestration behavior. They do not verify live Meta inference. The current Meta provider adapter is the only model provider implemented. Enterprise SaaS connectors and distributed execution are not claimed.
