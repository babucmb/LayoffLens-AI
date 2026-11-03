# Agent catalog

The runtime exposes ten agent specifications through `GET /api/agents`:

- Business Signal Intelligence
- External Research and Market Intelligence
- Financial Intelligence
- Project and Business Demand
- Workforce Capacity and Skills
- Infrastructure and Operational Intelligence
- Scenario and Forecasting
- Preventive Alternatives
- Evidence, Risk and Policy Review
- Executive Intelligence and Reporting

Each specification includes responsibility, objective, dedicated system
prompt, model role, permitted tool, and completion condition. The demo plan
selects only the bounded tools needed by the event policy; it does not claim
that every agent was invoked when it was not.
