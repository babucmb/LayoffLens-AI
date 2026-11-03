from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class IngestionRecord:
    source_id: str
    source_version: str
    evidence_id: str
    event_timestamp: str | None
    ingested_at: str
    provenance: str
    values: dict[str, Any]
    warnings: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class IngestionResult:
    source_id: str
    source_version: str
    snapshot_id: str
    records: tuple[IngestionRecord, ...]
    rejected: tuple[IngestionRecord, ...]
    warnings: tuple[str, ...]
    ingested_at: str
    provenance: str


class SourceAdapter(Protocol):
    source_name: str
    source_version: str

    def ingest(self) -> IngestionResult:
        ...


@dataclass(frozen=True)
class SourceSnapshot:
    source_name: str
    source_version: str
    snapshot_id: str
    source_timestamp: str | None
    ingested_at: str
    validation: dict[str, Any]
    data: dict[str, Any]
    provenance: str = "synthetic fixture"


def _stable_id(source_id: str, values: dict[str, Any]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{source_id}:{payload}".encode("utf-8")).hexdigest()[:16]
    return f"{source_id}:{digest}"


def _read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        raise ValueError("JSON source must contain an object or list of objects.")
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError("Only JSON and CSV source files are supported.")


class FileSourceAdapter:
    """Local JSON/CSV adapter; it is not an enterprise connector."""

    def __init__(
        self,
        path: str | Path,
        source_id: str,
        source_version: str,
        required_fields: tuple[str, ...],
        event_timestamp_field: str | None = "event_timestamp",
    ):
        self.path = Path(path)
        self.source_id = source_id
        self.source_version = source_version
        self.required_fields = required_fields
        self.event_timestamp_field = event_timestamp_field

    def ingest(self) -> IngestionResult:
        ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        raw_records = _read_records(self.path)
        accepted: list[IngestionRecord] = []
        rejected: list[IngestionRecord] = []
        warnings: list[str] = []
        for index, values in enumerate(raw_records):
            values = dict(values)
            provenance = f"{self.path.name}#record-{index + 1}"
            evidence_id = _stable_id(self.source_id, values)
            missing = [field for field in self.required_fields if not values.get(field)]
            record = IngestionRecord(
                source_id=self.source_id,
                source_version=self.source_version,
                evidence_id=evidence_id,
                event_timestamp=values.get(self.event_timestamp_field) if self.event_timestamp_field else None,
                ingested_at=ingested_at,
                provenance=provenance,
                values=values,
                warnings=tuple(["source event timestamp is unavailable"] if not values.get(self.event_timestamp_field) else []),
                error=f"Missing required fields: {', '.join(missing)}" if missing else None,
            )
            (rejected if missing else accepted).append(record)
            warnings.extend(record.warnings)
        content = json.dumps([record.values for record in accepted], sort_keys=True, separators=(",", ":"))
        snapshot_id = f"snapshot:{hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]}"
        return IngestionResult(
            source_id=self.source_id,
            source_version=self.source_version,
            snapshot_id=snapshot_id,
            records=tuple(accepted),
            rejected=tuple(rejected),
            warnings=tuple(sorted(set(warnings))),
            ingested_at=ingested_at,
            provenance=str(self.path),
        )


class SyntheticSourceAdapter:
    source_name = "synthetic-fixture"
    source_version = "synthetic-fixture-v1"

    def __init__(self, data: dict[str, Any], validation: dict[str, Any]):
        self.data = data
        self.validation = validation

    def ingest(self) -> IngestionResult:
        records = []
        for group, values in self.data.items():
            if not isinstance(values, list):
                continue
            for index, value in enumerate(values):
                if isinstance(value, dict):
                    records.append(
                        IngestionRecord(
                            source_id=f"{self.source_name}:{group}",
                            source_version=self.source_version,
                            evidence_id=value.get("id", _stable_id(group, value)),
                            event_timestamp=value.get("event_timestamp"),
                            ingested_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            provenance=f"synthetic fixture:{group}#{index + 1}",
                            values=value,
                            warnings=tuple([] if value.get("event_timestamp") else ["source event timestamp is unavailable"]),
                        )
                    )
        content = json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        return IngestionResult(
            source_id=self.source_name,
            source_version=self.source_version,
            snapshot_id=f"snapshot:{hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]}",
            records=tuple(records),
            rejected=(),
            warnings=("synthetic fixture has no source event timestamps",),
            ingested_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            provenance="synthetic fixture",
        )

    def snapshot(self) -> SourceSnapshot:
        result = self.ingest()
        return SourceSnapshot(
            source_name=result.source_id,
            source_version=result.source_version,
            snapshot_id=result.snapshot_id,
            source_timestamp=None,
            ingested_at=result.ingested_at,
            validation=self.validation,
            data=self.data,
            provenance=result.provenance,
        )


class ExternalResearchAdapter:
    """Explicitly local adapter for supplied research records.

    Network retrieval belongs behind a separately configured provider; this
    adapter never presents fixture records as live research.
    """

    source_name = "external-research"
    source_version = "external-research-v1"

    def __init__(self, records: list[dict[str, Any]]):
        self.records = records

    def ingest(self) -> IngestionResult:
        ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        accepted = tuple(
            IngestionRecord(
                source_id=self.source_name,
                source_version=self.source_version,
                evidence_id=value.get("record_id", _stable_id(self.source_name, value)),
                event_timestamp=value.get("publication_date"),
                ingested_at=ingested_at,
                provenance="supplied external research fixture",
                values=value,
                warnings=("external research is supplied locally; no live retrieval was performed",),
            )
            for value in self.records
            if isinstance(value, dict)
        )
        return IngestionResult(
            source_id=self.source_name,
            source_version=self.source_version,
            snapshot_id=f"snapshot:{hashlib.sha256(json.dumps(self.records, sort_keys=True).encode()).hexdigest()[:16]}",
            records=accepted,
            rejected=(),
            warnings=("external research adapter is local-only",),
            ingested_at=ingested_at,
            provenance="supplied external research fixture",
        )
