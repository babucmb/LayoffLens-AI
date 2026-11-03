# Agent architecture transformation

LayoffLens AI now has a connected local agent runtime in
`backend/app/agent_runtime.py`. The existing investigation API remains the
entry point, but its event-specific plan is executed through a registry of
validated tool contracts and independently described agent specifications.

The supervisor boundary is represented by the runtime plan: event context
selects the bounded plan, dependency checks run before each tool, each agent
has a responsibility, system prompt, objective, model role, permitted tool,
and completion condition, and execution produces a trace persisted with the
investigation. The deterministic specialists remain authoritative calculation
tools.

The default is `simulation`: no model or external network call is implied.
`/api/agents`, `/api/tools`, `/api/models`, and
`/api/investigations/{run_id}/trace` expose the architecture and actual trace.
The current local implementation does not claim autonomous live model
reasoning, live external research, or production scheduling.
