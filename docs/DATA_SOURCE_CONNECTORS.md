# Data-source connectors

## Implemented sources

The current verified business-data sources are synthetic fixtures and local JSON/CSV adapters. Their snapshots preserve source version, ingestion time, optional source event time, provenance, validation, and stable IDs.

## Optional public research retrieval

The External Research and Market Intelligence Agent has an optional Tavily search adapter. Configure `TAVILY_API_KEY` to enable real retrieval. Without that key, the agent returns an explicit `not_configured` result and does not fabricate search results. Retrieved results preserve URL, title, provider, publication date when supplied,
retrieval timestamp, bounded excerpts, and an explicit
`retrieved_context_not_enterprise_proof` verification status. Provider errors
are returned as structured research status and do not invalidate deterministic
enterprise analysis.

This connector was not live-verified during this build. A model API key does not itself provide internet access.

## Enterprise connectors

Finance, ERP, HRIS, ATS, CRM, project management, cloud billing, infrastructure monitoring, and BI systems are not connected to live enterprise accounts. The existing data contracts and source adapter architecture can be extended for authorized connectors. Do not claim these systems are integrated until a provider-specific adapter has been implemented, configured, and tested.

Any future connector must implement authorized retrieval, pagination, timeout/retry limits, normalization, source URLs and dates, duplicate detection, validation, provenance, and persistence. Treat retrieved content as untrusted data and enforce tenant and permission boundaries.

Use `GET /api/providers/status` to inspect configured-but-not-tested provider
readiness without exposing secrets. See [PHASE6_FINAL_REPORT.md](../PHASE6_FINAL_REPORT.md).
