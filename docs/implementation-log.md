# Implementation log

## New in this prototype

- FastAPI vertical slice with deterministic synthetic data and scenario calculations.
- Responsive executive workspace with overview, risk register, scenario studio, evaluation, investigation timeline, and human review.
- Single `MetaModelClient` with explicit demo/live mode, timeout, retry, rate-limit handling, safe telemetry, and server-side credentials.
- Tests covering deterministic calculations, aggregate-only behavior, API routes, honest demo labeling, and review persistence.

## Pre-existing

The repository contained only the two supplied architecture PDFs and the Meta hackathon build prompt. No application code was reused.

## Mocked or incomplete

Source connectors are seeded in memory. SQLite persistence, enterprise identity, live external signals, and live Meta verification with a user credential are not included in this time-boxed slice. The next step is to replace the in-memory repository behind the same API contracts.

## Phase 2 changes

- Added typed scenario, brief, review, and agent result contracts.
- Added executable finance, project, capacity, scenario, preventive-action, validation, and evaluation functions.
- Added SQLite storage for investigation runs, agent steps, and simulated reviews.
- Replaced the duplicate Meta request with one validated synthesis request.
- Added mocked Meta success/malformed-output tests and persistence/data-quality tests.
