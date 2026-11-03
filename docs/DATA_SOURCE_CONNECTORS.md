# Data-source connectors

The current verified sources are synthetic fixtures and local JSON/CSV
adapters. Their snapshots include source version, ingestion time, optional
source event time, provenance, validation, and stable IDs.

External research is represented in the agent/tool registry but no live search
provider is configured. A future connector must implement authorized
retrieval, pagination, timeout/retry limits, normalization, source URLs and
dates, duplicate detection, validation, and persistence. A model key alone
does not grant internet access.
