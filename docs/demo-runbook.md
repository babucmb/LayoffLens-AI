# LayoffLens AI demo runbook

## Prerequisites

- Windows PowerShell
- Python environment with `backend\requirements.txt` installed
- Node.js for the optional frontend syntax check
- No API key is required

From `D:\CMB_Desktop\LayoffLens_AI`:

```powershell
& C:\Users\MAHESH\anaconda3\python.exe -m pip install -r backend\requirements.txt
$env:META_MODEL_MODE="demo"
& C:\Users\MAHESH\anaconda3\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```

Open `http://127.0.0.1:8011/`.

## Repeatable walkthrough

1. Open **Overview** and point out that the records are synthetic, aggregate-only,
   and validated locally.
2. Open **Scenario studio**. Record the baseline, downside, and intervention
   cards.
3. Change project delay from 1 to 3 months and recalculate. The capacity gap
   should increase; this is endpoint sensitivity, not a confidence interval.
4. Increase mobility and recalculate. The aggregate Cloud gap should decrease.
5. Inspect the alternatives. Each card displays feasibility, gross savings,
   cost, net impact, assumptions, and limitations. The alternatives are
   mutually exclusive and must not be added together.
6. Click **Run investigation**. Inspect the source snapshot, policy version,
   specialist order, consumed inputs, evidence review, and final status.
7. Open **Human review**, inspect the run history, and record an explicitly
   supplied outcome with a date, value, and evidence note.
8. Compare the observation descriptively:

   ```powershell
   Invoke-RestMethod -Method Get `
     -Uri "http://127.0.0.1:8011/api/outcomes/compare/<RUN_ID>"
   ```

   Replace `<RUN_ID>` with the run ID shown in the history panel.

## Optional monitoring demonstration

Monitoring is disabled by default and is not required for the normal judge
demo. To enable the local-file reference workflow:

```powershell
$env:META_MODEL_MODE="demo"
$env:WRI_MONITOR_ENABLED="true"
$env:WRI_MONITOR_SOURCE_PATH="$pwd\data\monitor_snapshot.example.json"
$env:WRI_MONITOR_INTERVAL_SECONDS="30"
& C:\Users\MAHESH\anaconda3\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```

Check state with:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8011/api/monitor/status"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8011/api/monitor/check"
```

The first valid check reports `baseline`; the next unchanged check reports
`unchanged`. Edit a value in the fixture's `data` object, save it, and call
`POST /api/monitor/check` again. The result should report
`changed_investigated` and include a new run ID.

## Expected results

- Demo badge shows `Demo fallback`.
- No outbound Meta request is made.
- Optional live synthesis is not required; if live mode is unavailable, the UI
  remains deterministic and labels the fallback explicitly.
- Scenario output includes `evaluation` and `sensitivity`.
- Unsupported or unavailable inputs are labeled `insufficient_data`.
- Investigation budget exhaustion produces `incomplete`, not `complete`.
- A complete investigation includes the final evidence-review step.
- Replay uses the same snapshot but creates a new run ID.
- Outcome comparison is descriptive and explicitly makes no causal claim.

## Troubleshooting

- **Port is occupied:** use another port, then open that port in the browser.
- **Database permission or stale records:** set
  `$env:WRI_DATABASE_PATH="$pwd\demo-local.sqlite3"` before starting.
- **History is empty:** run an investigation first, then open **Human review**.
- **Outcome cannot be saved:** inspect a run first and provide both an
  observation date and evidence source.
- **Frontend does not refresh:** reload the page after restarting Uvicorn.
- **Live mode warning:** unset `META_MODEL_MODE` or set it to `demo`; do not
  provide credentials for this deterministic demonstration.
- **Live API verification:** do not enable live mode unless you have an
  authorized server-side key, explicit credit approval, and permission to send
  the synthetic evidence payload. Review [meta-api-integration.md](meta-api-integration.md)
  first. A successful mocked test is not a live verification.

## Claims to avoid

Do not claim live enterprise connectors, real-time monitoring, production
security, verified live Meta inference, causal impact, validated financial
savings, continuous learning, employee-level risk scoring, or automated
termination decisions. Those capabilities are not implemented or verified.
