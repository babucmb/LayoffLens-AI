# Orchestration design

The local orchestration boundary is implemented in
`backend/app/orchestration.py`.

## Deterministic planner

`DeterministicPlanner` selects a bounded, event-specific sequence:

- `project_delay`: project demand, capacity, scenario, preventive actions, finance,
  evidence review.
- `infrastructure_cost`: finance, scenario, preventive actions, project demand,
  capacity, evidence review.

Evidence review is always last. A budget can stop before it, which the API reports
as `incomplete`.

## Optional Meta planner

`MetaModelPlanner` validates a structured request but does not execute arbitrary
code or access files, shells, SQL, or unrestricted network tools. The default demo
does not call it. Any live model request remains behind the existing optional Meta
gateway and requires independent application validation.

Tool selection is not evidence validation. The application performs evidence
validation and final status calculation independently.
