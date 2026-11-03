# Investigation workflow

## Observable paths

The default dashboard request uses `project_delay`. A reproducible API request can
select another event:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/investigate `
  -ContentType 'application/json' `
  -Body '{"event_type":"infrastructure_cost","budget":4}'
```

The response contains `event`, `steps`, each step's `reason` and `inputs`, an
`investigation_status`, and a `review` object. Project-delay runs begin with
`Project demand analyst`; infrastructure cost runs begin with `Finance analyst`.
Both remain aggregate-only.

The budget is bounded from 1 through 6. The policy does not repeat completed work.
The `Evidence and policy reviewer` is mandatory. If the budget ends before that
step, the result is `incomplete`, not complete. Failed upstream work is visible in
the step result and planner limitations; it makes the run `degraded`.

The local source adapter records a stable content-based snapshot ID separately from
the ingestion timestamp. Replay with `snapshot_id` reuses that stored historical
input; it does not overwrite the historical snapshot. A new event can be replayed
with a new `event_id`, and the resulting run gets a new run ID while retaining the
snapshot and policy references.

The JSON/CSV adapter is a local file interface only. The repository includes
representative fixtures for finance, projects, capacity, hiring, and investment;
no external connector is enabled.

The history API also returns persisted specialist steps and explicitly supplied
outcome observations. Outcomes are observations, not forecasts, and the system
does not infer that a recommendation caused an outcome.

## Scenario evaluation

`POST /api/scenarios` returns the existing baseline, downside, and user-selected
intervention results plus an `evaluation` object and deterministic `sensitivity`
object. The evaluation includes four mutually exclusive alternatives:

- discretionary spending reduction: 5% of latest monthly opex
- project reprioritization: 8% of weighted pipeline less a 1% transition cost
- hiring-plan adjustment: 0.06 USD million per approved seat
- internal redeployment: 0.18 USD million of illustrative avoided-gap value per
  aggregate unit, less 0.09 USD million transition cost

All values are illustrative USD millions unless explicitly labeled as aggregate
capacity units. The response records gross savings, costs, net savings, a
12-month financial horizon, a 0-3 month capacity view, assumptions, limitations,
and calculation version `scenario-evaluation-v1`. Alternatives are comparison
cases and their savings must not be summed. Only feasible and sufficiently
evidenced alternatives are ranked using published weights for feasibility,
net impact, evidence completeness, and reversibility.

Sensitivity is endpoint analysis over declared bounds, not a calibrated
confidence interval. The outcome comparison endpoint reports descriptive
observed-versus-projected differences and explicitly makes no causal claim.

For a complete result, evidence review must finish with no unsupported references,
all required steps must succeed, and the final brief's evidence IDs must be drawn
from the validated source inventory.
