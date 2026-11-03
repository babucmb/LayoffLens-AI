# Agent runtime demo runbook

1. Start the deterministic demo using the commands in
   [demo-runbook.md](demo-runbook.md).
2. Open the dashboard and select **Run investigation**.
3. Inspect the investigation panel. It now shows the actual agent runtime
   trace, selected registered tools, reasons, evidence IDs, handoffs, and the
   independent evidence-review status.
4. Open `/api/agents` to inspect the supervisor and ten agent specifications.
5. Open `/api/tools` to inspect input/output contract metadata, permissions,
   dependencies, and read-only flags.
6. Open `/api/investigations/{run_id}/trace` using the run ID shown in the
   panel to inspect persisted trace data.
7. Use the existing scenario, outcome, history, and human-review views.

The demo is deterministic simulation. Do not describe the trace as live model
reasoning, live external research, or a production autonomous agent.
