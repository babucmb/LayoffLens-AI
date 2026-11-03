# Agent execution flow

1. An investigation request or local monitor change enters the existing API.
2. The event policy creates a bounded dynamic plan.
3. `AgentRuntime` validates the selected registered tool and dependencies.
4. The selected specialist invokes deterministic aggregate calculations.
5. Results, evidence, inputs, and handoffs are recorded in agent steps.
6. The evidence/policy review remains a mandatory completion gate.
7. The trace is persisted and exposed in history and the frontend.

Budget exhaustion remains `incomplete`; failed specialists remain `degraded`.
Replay creates a distinct run. No agent can execute arbitrary code or approve
an employment action.
