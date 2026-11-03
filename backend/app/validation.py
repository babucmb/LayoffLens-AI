from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def validate_data(data: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for group, required in (
        ("finance", ("id", "revenue", "budget", "opex")),
        ("projects", ("id", "weighted", "skill", "status")),
        ("capacity", ("skill", "capacity", "demand")),
        ("hiring", ("id", "skill", "seats", "join_month")),
    ):
        for index, record in enumerate(data.get(group, [])):
            missing = [field for field in required if field not in record]
            numeric_errors = [field for field in required if field in record and field in {"revenue", "budget", "opex", "weighted", "capacity", "demand", "seats"} and not isinstance(record[field], (int, float))]
            checks.append({"source": group, "index": index, "valid": not missing and not numeric_errors, "missing": missing, "numeric_errors": numeric_errors})
    valid = all(item["valid"] for item in checks)
    return {"valid": valid, "records": checks, "freshness": "synthetic_seed", "warning": "Seeded records have no ingestion timestamp; freshness is not asserted."}
