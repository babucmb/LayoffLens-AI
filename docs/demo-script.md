# LayoffLens AI three-minute demo script

## 0:00–0:30 — Problem

“LayoffLens AI helps a planning team inspect aggregate business pressure before
considering workforce reductions. It combines synthetic finance, project,
capacity, hiring, and infrastructure signals. It does not score employees or
make termination decisions.”

## 0:30–1:05 — Architecture

“The local source adapter validates records and creates stable evidence IDs and
snapshots. Deterministic specialists analyze project demand, finance, and
capacity. A bounded planner passes structured results to scenario and action
analysis. The demo uses SQLite and no network calls.”

## 1:05–1:45 — Evidence-driven investigation

Click **Run investigation** and show the source snapshot, policy version,
specialist statuses, consumed inputs, evidence IDs, and final evidence review.

“A complete result requires evidence review. A budget that ends earlier is
reported as incomplete, and failed or unsupported checks are degraded.”

## 1:45–2:25 — Scenario comparison

Open **Scenario studio**. Show baseline, downside, and intervention. Increase
delay, recalculate, then add mobility.

“The four alternatives are comparison cases: spending reduction, project
reprioritization, hiring-plan adjustment, and internal redeployment. Costs,
gross savings, net savings, units, assumptions, limitations, and explicit
ranking weights are visible. Their savings are not additive.”

## 2:25–2:45 — Human review and observation

Open **Human review**, inspect history, and save an explicitly supplied outcome.
Show the descriptive projection comparison.

“The observed-versus-projected difference is not treated as causal impact and
does not automatically update policy.”

## 2:45–3:00 — Limitations

“This is a deterministic synthetic-data prototype. Enterprise connectors,
production security, calibrated forecasts, validated savings, live Meta
inference, causal inference, and automated employment decisions are not
implemented. A human reviewer remains responsible for any decision.”
