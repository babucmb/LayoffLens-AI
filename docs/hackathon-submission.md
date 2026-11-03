# LayoffLens AI — Enterprise Workforce Resilience Intelligence

## One-line pitch

An evidence-driven AI system that helps enterprises detect operational
disruption early, investigate root causes, simulate alternatives, and support
responsible human decisions before workforce reductions become necessary.

## Problem and solution

Organizations often react to financial and operational pressure too late.
Disconnected data, delayed investigations, and limited visibility into
reversible alternatives make it difficult to protect continuity and workforce
capability. LayoffLens AI combines synthetic enterprise intelligence,
deterministic forecasting, bounded specialist agents, scenario simulation,
evidence governance, and human review in one local application.

## Differentiation

- Evidence-backed multi-domain investigations
- Deterministic calculations for authoritative numeric outputs
- Preventive alternatives such as mobility, reskilling, and infrastructure review
- Explicit uncertainty, missing evidence, and data provenance
- Human approval and auditable review lifecycle
- Optional Meta executive synthesis and optional public research context
- Aggregate-only workforce data with no named employee recommendations

## Meta AI contribution

Meta integration is optional. In demo mode, the application makes no model
request and uses deterministic fallback output. The live Responses API adapter,
structured output validation, raw response parsing, and failure handling are
mock-tested but no live request was authorized or executed for this submission.
Meta does not control calculations, evidence validation, scenario feasibility, or
human decisions.

## Impact and limitations

The product can help planning teams identify risks earlier, compare continuity
options, preserve delivery capability, and make better-informed decisions.
Values are synthetic fixtures and illustrative estimates. Tavily public research
is contextual rather than proof of a private enterprise event. Local demo
authentication is not SSO, SQLite audit storage is not tamper-proof, and no
automated employment action is implemented.

## Run and verify

```powershell
cd D:\CMB_Desktop\LayOffLens_AI_Admin
& C:\Users\MAHESH\anaconda3\python.exe -m pip install -r backend\requirements.txt
$env:META_MODEL_MODE="demo"
$env:WRI_AGENT_MODE="simulation"
& C:\Users\MAHESH\anaconda3\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```

Open `http://127.0.0.1:8011/`. API documentation is available at
`http://127.0.0.1:8011/docs`. Run the full validation with
`& C:\Users\MAHESH\anaconda3\python.exe -m pytest -q`.
