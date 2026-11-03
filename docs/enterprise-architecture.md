# Target-state enterprise architecture

## Current local reference slice

The current application implements a local reference slice of this target:
synthetic source snapshotting, deterministic bounded orchestration, final evidence
review, SQLite investigation history, and optional Meta synthesis behind an explicit
mode switch. `/api/events/replay` replays synthetic events and `/api/history` reads
persisted investigation metadata.

These are not live enterprise connectors or production audit controls. Synthetic
records do not contain source timestamps, so freshness is not asserted; the local
adapter records ingestion time and a reproducible snapshot ID instead.

Source adapters (ERP/finance, CRM, project portfolio, ATS/HRIS, LMS/skills, FinOps/cloud, procurement, and authorized public sources) emit versioned records into raw, validated, curated, evidence, and feature zones. Schema validation, freshness, lineage, retries, and dead-letter handling sit at ingestion.

Deterministic analytics calculate financial variance, time-series baselines, change detection, aggregate capacity, scenarios, sensitivity, and evaluation. Bounded domain agents call allowlisted functions. A model gateway handles Meta authentication, timeout, rate limit, output validation, telemetry, cost budget, and safe fallback. The decision product exposes overview, risk register, scenario studio, evidence, human review, and outcome evaluation.

Production deployment would add SSO/RBAC, encryption, retention, tenant isolation, secrets management, observability, incident response, model evaluation, and rollback. No agent may access arbitrary SQL, shell, named employee records, or employment action systems.
