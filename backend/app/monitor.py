from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from .persistence import Repository
from .sources import SourceSnapshot
from .validation import validate_data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def monitor_fingerprint(envelope: dict[str, Any]) -> str:
    content = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_monitor_snapshot(path: str | Path) -> tuple[dict[str, Any], SourceSnapshot, dict[str, Any]]:
    source_path = Path(path)
    if source_path.suffix.lower() != ".json":
        raise ValueError("Monitor source must be a JSON file.")
    if not source_path.exists():
        raise ValueError(f"Monitor source does not exist: {source_path}")
    try:
        envelope = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Monitor source could not be read: {exc}") from exc
    if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
        raise ValueError("Monitor source must be an object with a data object.")
    source_id = envelope.get("source_id", "local-monitor")
    source_version = envelope.get("source_version", "local-monitor-v1")
    event_type = envelope.get("event_type", "project_delay")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("Monitor source_id must be a non-empty string.")
    if not isinstance(source_version, str) or not source_version:
        raise ValueError("Monitor source_version must be a non-empty string.")
    if not isinstance(event_type, str) or event_type not in {"project_delay", "infrastructure_cost"}:
        raise ValueError("Monitor event_type must be project_delay or infrastructure_cost.")
    data = envelope["data"]
    validation = validate_data(data)
    content = json.dumps(data, sort_keys=True, separators=(",", ":"))
    snapshot_id = f"snapshot:{hashlib.sha256(f'{source_id}:{source_version}:{content}'.encode('utf-8')).hexdigest()[:16]}"
    snapshot = SourceSnapshot(
        source_name=source_id,
        source_version=source_version,
        snapshot_id=snapshot_id,
        source_timestamp=envelope.get("source_timestamp"),
        ingested_at=utc_now(),
        validation=validation,
        data=data,
        provenance=str(source_path),
    )
    return envelope, snapshot, validation


class LocalMonitor:
    def __init__(
        self,
        repository: Repository,
        source_path: str | Path,
        investigate: Callable[[Any, dict[str, Any], dict[str, Any], SourceSnapshot], Awaitable[dict[str, Any]]],
    ):
        self.repository = repository
        self.source_path = str(source_path)
        self.investigate = investigate

    def configuration(self, enabled: bool, interval_seconds: int) -> dict[str, Any]:
        return {
            "enabled": enabled,
            "source_path": self.source_path,
            "interval_seconds": interval_seconds,
            "mode": "local JSON polling",
        }

    async def check(self) -> dict[str, Any]:
        checked_at = utc_now()
        try:
            envelope, snapshot, validation = read_monitor_snapshot(self.source_path)
            fingerprint = monitor_fingerprint(envelope)
            previous = self.repository.monitor_state()
            self.repository.save_snapshot({
                "snapshot_id": snapshot.snapshot_id,
                "source_id": snapshot.source_name,
                "source_version": snapshot.source_version,
                "ingested_at": snapshot.ingested_at,
                "source_timestamp": snapshot.source_timestamp,
                "provenance": snapshot.provenance,
                "validation": validation,
                "data": snapshot.data,
            })
            if not validation["valid"]:
                state = {
                    "fingerprint": fingerprint,
                    "snapshot_id": snapshot.snapshot_id,
                    "last_checked_at": checked_at,
                    "last_changed_at": previous.get("last_changed_at") if previous else None,
                    "status": "invalid_data",
                    "last_run_id": previous.get("last_run_id") if previous else None,
                    "error": validation.get("warning", "Monitor data failed validation."),
                }
                self.repository.save_monitor_state(state)
                return {"status": "invalid_data", "investigation_triggered": False, "validation": validation, **state}
            if previous and previous.get("fingerprint") == fingerprint:
                state = {
                    **previous,
                    "last_checked_at": checked_at,
                    "status": "unchanged",
                    "error": None,
                }
                self.repository.save_monitor_state(state)
                return {"status": "unchanged", "investigation_triggered": False, **state}
            if previous is None:
                state = {
                    "fingerprint": fingerprint,
                    "snapshot_id": snapshot.snapshot_id,
                    "last_checked_at": checked_at,
                    "last_changed_at": checked_at,
                    "status": "baseline",
                    "last_run_id": None,
                    "error": None,
                }
                self.repository.save_monitor_state(state)
                return {"status": "baseline", "investigation_triggered": False, "validation": validation, **state}
            from .schemas import InvestigationRequest

            request = InvestigationRequest(
                event_type=envelope["event_type"],
                budget=6,
                event_id=f"monitor:{fingerprint}",
            )
            run = await self.investigate(request, snapshot.data, validation, snapshot)
            state = {
                "fingerprint": fingerprint,
                "snapshot_id": snapshot.snapshot_id,
                "last_checked_at": checked_at,
                "last_changed_at": checked_at,
                "status": "changed_investigated" if previous else "baseline",
                "last_run_id": run["run_id"] if previous else None,
                "error": None,
            }
            self.repository.save_monitor_state(state)
            return {
                "status": state["status"],
                "investigation_triggered": previous is not None,
                "run_id": run["run_id"] if previous else None,
                "validation": validation,
                **state,
            }
        except (OSError, ValueError) as exc:
            previous = self.repository.monitor_state() or {}
            state = {
                **previous,
                "last_checked_at": checked_at,
                "status": "error",
                "error": str(exc),
            }
            self.repository.save_monitor_state(state)
            return {"status": "error", "investigation_triggered": False, **state}
