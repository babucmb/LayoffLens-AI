from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class Repository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS investigation_runs (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, mode TEXT NOT NULL,
                    model TEXT NOT NULL, scenario_json TEXT NOT NULL, brief_json TEXT NOT NULL,
                    event_json TEXT NOT NULL DEFAULT '{}',
                    source_json TEXT NOT NULL DEFAULT '{}',
                    policy_json TEXT NOT NULL DEFAULT '{}',
                    evaluation_json TEXT NOT NULL DEFAULT '{}',
                    trace_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS agent_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    agent TEXT NOT NULL, status TEXT NOT NULL, evidence_json TEXT NOT NULL,
                    result_json TEXT NOT NULL, error TEXT, FOREIGN KEY(run_id) REFERENCES investigation_runs(id)
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, reviewer TEXT NOT NULL,
                    recommendation TEXT NOT NULL, rationale TEXT NOT NULL, model TEXT NOT NULL, evidence_json TEXT NOT NULL,
                    investigation_id TEXT, scenario_id TEXT, actor TEXT, role TEXT, tenant_id TEXT,
                    lifecycle_status TEXT NOT NULL DEFAULT 'open', evidence_snapshot_json TEXT NOT NULL DEFAULT '{}'
                    ,assigned_reviewer TEXT, assigned_role TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS review_activity (
                    id TEXT PRIMARY KEY, review_id TEXT NOT NULL, created_at TEXT NOT NULL,
                    activity_type TEXT NOT NULL, actor TEXT NOT NULL, role TEXT NOT NULL,
                    tenant_id TEXT NOT NULL, detail_json TEXT NOT NULL,
                    FOREIGN KEY(review_id) REFERENCES reviews(id)
                );
                CREATE TABLE IF NOT EXISTS source_snapshots (
                    snapshot_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
                    source_version TEXT NOT NULL, ingested_at TEXT NOT NULL,
                    source_timestamp TEXT, provenance TEXT NOT NULL,
                    validation_json TEXT NOT NULL, data_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ingested_events (
                    event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL, snapshot_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outcome_observations (
                    id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL,
                    category TEXT NOT NULL, value REAL, unit TEXT,
                    observed_on TEXT NOT NULL, evidence_source TEXT NOT NULL,
                    provenance TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS monitor_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    fingerprint TEXT,
                    snapshot_id TEXT,
                    last_checked_at TEXT,
                    last_changed_at TEXT,
                    status TEXT NOT NULL,
                    last_run_id TEXT,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS work_items (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 2,
                    payload_json TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(work_id) REFERENCES work_items(id)
                );
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    evaluation_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dataset_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    limitations_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    role TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    target_id TEXT,
                    correlation_id TEXT
                );
                CREATE TABLE IF NOT EXISTS scenario_runs (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, actor TEXT NOT NULL,
                    scenario_type TEXT NOT NULL, source_snapshot_id TEXT, calculation_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'needs_review',
                    role TEXT, tenant_id TEXT NOT NULL DEFAULT 'demo-tenant'
                );
                CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps(run_id);
                CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at);
                CREATE INDEX IF NOT EXISTS idx_work_timeline_work ON work_timeline(work_id);
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(investigation_runs)")}
            if "event_json" not in columns:
                db.execute("ALTER TABLE investigation_runs ADD COLUMN event_json TEXT NOT NULL DEFAULT '{}'")
            if "source_json" not in columns:
                db.execute("ALTER TABLE investigation_runs ADD COLUMN source_json TEXT NOT NULL DEFAULT '{}'")
            if "policy_json" not in columns:
                db.execute("ALTER TABLE investigation_runs ADD COLUMN policy_json TEXT NOT NULL DEFAULT '{}'")
            if "evaluation_json" not in columns:
                db.execute("ALTER TABLE investigation_runs ADD COLUMN evaluation_json TEXT NOT NULL DEFAULT '{}'")
            if "trace_json" not in columns:
                db.execute("ALTER TABLE investigation_runs ADD COLUMN trace_json TEXT NOT NULL DEFAULT '[]'")
            review_columns = {row["name"] for row in db.execute("PRAGMA table_info(reviews)")}
            for name, definition in (
                ("investigation_id", "TEXT"),
                ("scenario_id", "TEXT"),
                ("actor", "TEXT"),
                ("role", "TEXT"),
                ("tenant_id", "TEXT"),
                ("lifecycle_status", "TEXT NOT NULL DEFAULT 'open'"),
                ("evidence_snapshot_json", "TEXT NOT NULL DEFAULT '{}'"),
                ("assigned_reviewer", "TEXT"),
                ("assigned_role", "TEXT"),
                ("updated_at", "TEXT"),
            ):
                if name not in review_columns:
                    db.execute(f"ALTER TABLE reviews ADD COLUMN {name} {definition}")
            # Legacy reviews predate actor/tenant fields. Keep them in the
            # original demo tenant rather than making NULL rows visible to
            # every tenant.
            db.execute("UPDATE reviews SET actor = COALESCE(actor, reviewer), role = COALESCE(role, 'reviewer'), tenant_id = COALESCE(tenant_id, 'demo-tenant')")
            scenario_columns = {row["name"] for row in db.execute("PRAGMA table_info(scenario_runs)")}
            if "role" not in scenario_columns:
                db.execute("ALTER TABLE scenario_runs ADD COLUMN role TEXT")
            if "tenant_id" not in scenario_columns:
                db.execute("ALTER TABLE scenario_runs ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'demo-tenant'")
            audit_columns = {row["name"] for row in db.execute("PRAGMA table_info(audit_events)")}
            if "target_id" not in audit_columns:
                db.execute("ALTER TABLE audit_events ADD COLUMN target_id TEXT")
            if "correlation_id" not in audit_columns:
                db.execute("ALTER TABLE audit_events ADD COLUMN correlation_id TEXT")

    def save_investigation(self, run: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO investigation_runs (id, created_at, mode, model, scenario_json, brief_json, event_json, source_json, policy_json, evaluation_json, trace_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run["run_id"], run["timestamp"], run["mode"], run["model"], json.dumps(run["scenario"]), json.dumps(run["brief"]), json.dumps(run.get("event", {})), json.dumps(run.get("source", {})), json.dumps(run.get("policy", {})), json.dumps(run.get("scenario_evaluation", {})), json.dumps(run.get("agent_trace", []))))
            db.executemany("INSERT INTO agent_steps(run_id, agent, status, evidence_json, result_json, error) VALUES (?, ?, ?, ?, ?, ?)", [(run["run_id"], s["agent"], s["status"], json.dumps({"ids": s["evidence"], "reason": s.get("reason", ""), "inputs": s.get("inputs", [])}), json.dumps(s.get("result", {})), s.get("error")) for s in run["steps"]])

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO source_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot["snapshot_id"], snapshot["source_id"], snapshot["source_version"],
                    snapshot["ingested_at"], snapshot.get("source_timestamp"),
                    snapshot["provenance"], json.dumps(snapshot["validation"]),
                    json.dumps(snapshot["data"]),
                ),
            )

    def save_scenario(self, scenario: dict[str, Any], actor: str = "anonymous",
                      role: str = "admin", tenant_id: str = "demo-tenant") -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO scenario_runs (id, created_at, actor, scenario_type, source_snapshot_id, calculation_version, payload_json, role, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (scenario["scenario_id"], scenario["created_at"], actor, scenario["scenario_type"], scenario.get("source_snapshot_id"), scenario["calculation_version"], json.dumps(scenario), role, tenant_id),
            )

    def scenarios(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload_json, review_status, actor, role, tenant_id FROM scenario_runs ORDER BY created_at ASC").fetchall()
        return [{**json.loads(row["payload_json"]), "review_status": row["review_status"], "actor": row["actor"], "role": row["role"], "tenant_id": row["tenant_id"]} for row in rows]

    def scenario(self, scenario_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as db:
            if tenant_id:
                row = db.execute("SELECT payload_json, review_status, actor, role, tenant_id FROM scenario_runs WHERE id = ? AND tenant_id = ?", (scenario_id, tenant_id)).fetchone()
            else:
                row = db.execute("SELECT payload_json, review_status, actor, role, tenant_id FROM scenario_runs WHERE id = ?", (scenario_id,)).fetchone()
        if row is None:
            return None
        return {**json.loads(row["payload_json"]), "review_status": row["review_status"], "actor": row["actor"], "role": row["role"], "tenant_id": row["tenant_id"]}

    def save_monitor_state(self, state: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
            """
            INSERT INTO monitor_state
                (id, fingerprint, snapshot_id, last_checked_at, last_changed_at, status, last_run_id, error)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                fingerprint=excluded.fingerprint,
                snapshot_id=excluded.snapshot_id,
                last_checked_at=excluded.last_checked_at,
                last_changed_at=excluded.last_changed_at,
                status=excluded.status,
                last_run_id=excluded.last_run_id,
                error=excluded.error
            """,
            (
                state.get("fingerprint"), state.get("snapshot_id"),
                state.get("last_checked_at"), state.get("last_changed_at"),
                state.get("status", "never_checked"), state.get("last_run_id"),
                state.get("error"),
            ),
            )

    def monitor_state(self) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM monitor_state WHERE id = 1").fetchone()
        return dict(row) if row else None

    def snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM source_snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        if row is None:
            return None
        return {
            **dict(row),
            "validation": json.loads(row["validation_json"]),
            "data": json.loads(row["data_json"]),
        }

    def snapshots(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT snapshot_id, source_id, source_version, ingested_at, source_timestamp, provenance FROM source_snapshots ORDER BY ingested_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_event(self, event: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO ingested_events VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event["event_id"], event["event_type"], json.dumps(event["payload"]),
                    event["snapshot_id"], event["policy_version"], event["created_at"],
                ),
            )

    def event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM ingested_events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        return {**dict(row), "payload": json.loads(row["payload_json"])}

    def create_work_item(self, item: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as db:
            existing = db.execute("SELECT * FROM work_items WHERE event_id = ?", (item["event_id"],)).fetchone()
            if existing is None:
                db.execute(
                    """INSERT INTO work_items
                    (id, event_id, status, attempts, max_attempts, payload_json, result_json, error, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, '{}', NULL, ?, ?)""",
                    (
                        item["id"], item["event_id"], item.get("status", "queued"),
                        item.get("attempts", 0), item.get("max_attempts", 2),
                        json.dumps(item.get("payload", {})), item["created_at"], item["updated_at"],
                    ),
                )
                db.execute(
                    "INSERT INTO work_timeline (work_id, status, detail, created_at) VALUES (?, ?, ?, ?)",
                    (item["id"], item.get("status", "queued"), "Work item accepted.", item["created_at"]),
                )
                existing = db.execute("SELECT * FROM work_items WHERE id = ?", (item["id"],)).fetchone()
        return self._work_item(existing)

    @staticmethod
    def _work_item(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        item["result"] = json.loads(item.pop("result_json"))
        return item

    def work_item(self, work_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM work_items WHERE id = ?", (work_id,)).fetchone()
        return self._work_item(row)

    def work_item_for_event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM work_items WHERE event_id = ?", (event_id,)).fetchone()
        return self._work_item(row)

    def update_work_item(self, work_id: str, status: str, updated_at: str, *, detail: str = "", error: str | None = None, result: dict[str, Any] | None = None, increment_attempt: bool = False) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT attempts FROM work_items WHERE id = ?", (work_id,)).fetchone()
            if row is None:
                return None
            db.execute(
                """UPDATE work_items SET status = ?, attempts = attempts + ?, updated_at = ?,
                error = ?, result_json = ? WHERE id = ?""",
                (status, 1 if increment_attempt else 0, updated_at, error, json.dumps(result or {}), work_id),
            )
            db.execute(
                "INSERT INTO work_timeline (work_id, status, detail, created_at) VALUES (?, ?, ?, ?)",
                (work_id, status, detail or None, updated_at),
            )
            updated = db.execute("SELECT * FROM work_items WHERE id = ?", (work_id,)).fetchone()
        return self._work_item(updated)

    def work_items(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM work_items ORDER BY created_at ASC").fetchall()
        return [self._work_item(row) for row in rows]

    def work_timeline(self, work_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT work_id, status, detail, created_at FROM work_timeline WHERE work_id = ? ORDER BY id ASC", (work_id,)).fetchall()
        return [dict(row) for row in rows]

    def save_evaluation(self, evaluation: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO evaluation_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    evaluation["id"], evaluation["created_at"],
                    evaluation["evaluation_version"], evaluation["policy_version"],
                    evaluation["status"], json.dumps(evaluation["dataset"]),
                    json.dumps(evaluation["metrics"]), json.dumps(evaluation["limitations"]),
                ),
            )

    def evaluations(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM evaluation_runs ORDER BY created_at ASC").fetchall()
        return [
            {
                **dict(row),
                "dataset": json.loads(row["dataset_json"]),
                "metrics": json.loads(row["metrics_json"]),
                "limitations": json.loads(row["limitations_json"]),
            }
            for row in rows
        ]

    def save_audit_event(self, event: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO audit_events (id, created_at, action, actor, role, tenant_id, detail_json, target_id, correlation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event["id"], event["created_at"], event["action"],
                    event["actor"], event["role"], event["tenant_id"],
                    json.dumps(event.get("detail", {})), event.get("target_id"),
                    event.get("correlation_id"),
                ),
            )

    def audit_events(self, *, tenant_id: str | None = None, actor: str | None = None,
                     role: str | None = None, action: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            clauses: list[str] = []
            args: list[str] = []
            for column, value in (("tenant_id", tenant_id), ("actor", actor), ("role", role), ("action", action)):
                if value:
                    clauses.append(f"{column} = ?")
                    args.append(value)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = db.execute(f"SELECT * FROM audit_events{where} ORDER BY created_at ASC", args).fetchall()
        return [
            {**dict(row), "detail": json.loads(row["detail_json"])}
            for row in rows
        ]

    def recover_work_items(self, updated_at: str) -> int:
        with self._connect() as db:
            rows = db.execute("SELECT id FROM work_items WHERE status IN ('queued', 'running', 'retrying')").fetchall()
            for row in rows:
                db.execute("UPDATE work_items SET status = 'queued', error = ?, updated_at = ? WHERE id = ?", ("Recovered after process restart.", updated_at, row["id"]))
                db.execute("INSERT INTO work_timeline (work_id, status, detail, created_at) VALUES (?, 'queued', ?, ?)", (row["id"], "Recovered after process restart.", updated_at))
        return len(rows)

    def save_outcome(self, outcome: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO outcome_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    outcome["id"], outcome["investigation_id"], outcome["category"],
                    outcome.get("value"), outcome.get("unit"), outcome["observed_on"],
                    outcome["evidence_source"], outcome["provenance"], outcome["created_at"],
                ),
            )

    def outcomes(self, investigation_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if investigation_id:
                rows = db.execute(
                    "SELECT * FROM outcome_observations WHERE investigation_id = ? ORDER BY created_at ASC",
                    (investigation_id,),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM outcome_observations ORDER BY created_at ASC").fetchall()
        return [dict(row) for row in rows]

    def save_review(self, entry: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO reviews
                (id, created_at, reviewer, recommendation, rationale, model, evidence_json,
                 investigation_id, scenario_id, actor, role, tenant_id, lifecycle_status,
                 evidence_snapshot_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["id"], entry["timestamp"], entry.get("reviewer", entry.get("actor", "anonymous")),
                    entry["recommendation"], entry["rationale"], entry.get("model", "deterministic"),
                    json.dumps(entry.get("evidence", [])), entry.get("investigation_id"),
                    entry.get("scenario_id"), entry.get("actor"), entry.get("role"),
                    entry.get("tenant_id"), entry.get("lifecycle_status", "open"),
                    json.dumps(entry.get("evidence_snapshot", {})),
                    entry.get("updated_at", entry["timestamp"]),
                ),
            )

    def review(self, review_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as db:
            query = "SELECT * FROM reviews WHERE id = ?"
            args: list[Any] = [review_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                args.append(tenant_id)
            row = db.execute(query, args).fetchone()
            if row is None:
                return None
            activities = db.execute(
                "SELECT * FROM review_activity WHERE review_id = ? ORDER BY created_at ASC, id ASC",
                (review_id,),
            ).fetchall()
        result = {**dict(row), "evidence": json.loads(row["evidence_json"]),
                  "evidence_snapshot": json.loads(row["evidence_snapshot_json"] or "{}")}
        result["activity"] = [{**dict(item), "detail": json.loads(item["detail_json"])} for item in activities]
        return result

    def investigations(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM investigation_runs ORDER BY created_at ASC").fetchall()
            step_rows = db.execute("SELECT * FROM agent_steps ORDER BY id ASC").fetchall()
        steps_by_run: dict[str, list[dict[str, Any]]] = {}
        for row in step_rows:
            evidence = json.loads(row["evidence_json"])
            steps_by_run.setdefault(row["run_id"], []).append({
                "agent": row["agent"], "status": row["status"],
                "evidence": evidence.get("ids", []), "reason": evidence.get("reason", ""),
                "inputs": evidence.get("inputs", []), "result": json.loads(row["result_json"]),
                "error": row["error"],
            })
        return [
            {
                **dict(row),
                "scenario": json.loads(row["scenario_json"]),
                "brief": json.loads(row["brief_json"]),
                "event": json.loads(row["event_json"]),
                "source": json.loads(row["source_json"]),
                "policy": json.loads(row["policy_json"]),
                "scenario_evaluation": json.loads(row["evaluation_json"]),
                "agent_trace": json.loads(row["trace_json"]),
                "steps": steps_by_run.get(row["id"], []),
                "outcomes": self.outcomes(row["id"]),
            }
            for row in rows
        ]

    def reviews(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if tenant_id:
                rows = db.execute("SELECT * FROM reviews WHERE tenant_id = ? ORDER BY created_at ASC", (tenant_id,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM reviews ORDER BY created_at ASC").fetchall()
        return [{**dict(row), "evidence": json.loads(row["evidence_json"]),
                 "evidence_snapshot": json.loads(row["evidence_snapshot_json"] or "{}")}
                for row in rows]

    def update_review(self, review_id: str, *, status: str | None = None,
                      recommendation: str | None = None, rationale: str | None = None,
                      evidence_snapshot: dict[str, Any] | None = None,
                      assigned_reviewer: str | None = None,
                      assigned_role: str | None = None) -> bool:
        fields: list[str] = []
        values: list[Any] = []
        if status is not None:
            fields.append("lifecycle_status = ?"); values.append(status)
        if recommendation is not None:
            fields.append("recommendation = ?"); values.append(recommendation)
        if rationale is not None:
            fields.append("rationale = ?"); values.append(rationale)
        if evidence_snapshot is not None:
            fields.append("evidence_snapshot_json = ?"); values.append(json.dumps(evidence_snapshot))
        if assigned_reviewer is not None:
            fields.append("assigned_reviewer = ?"); values.append(assigned_reviewer)
        if assigned_role is not None:
            fields.append("assigned_role = ?"); values.append(assigned_role)
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if not fields:
            return False
        values.append(review_id)
        with self._connect() as db:
            cursor = db.execute(f"UPDATE reviews SET {', '.join(fields)} WHERE id = ?", values)
        return cursor.rowcount > 0

    def add_review_activity(self, review_id: str, activity: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO review_activity
                (id, review_id, created_at, activity_type, actor, role, tenant_id, detail_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (activity["id"], review_id, activity["created_at"], activity["activity_type"],
                 activity["actor"], activity["role"], activity["tenant_id"],
                 json.dumps(activity.get("detail", {}))),
            )
