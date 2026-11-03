from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any


HORIZONS = {30: 1, 90: 3, 180: 6, 365: 12}


def _pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)


def _trend(rows: list[dict[str, Any]], value: str, *, actual: str | None = None) -> dict[str, Any]:
    values = [float(row.get(value, 0) or 0) for row in rows]
    latest = values[-1] if values else None
    previous = values[-2] if len(values) > 1 else None
    average = sum(values) / len(values) if values else None
    return {
        "metric": value, "observations": len(values), "latest": latest,
        "previous": previous, "absolute_change": round(latest - previous, 4) if latest is not None and previous is not None else None,
        "percentage_change": _pct(latest, previous) if latest is not None and previous is not None else None,
        "rolling_average": round(average, 4) if average is not None else None,
        "reporting_period": rows[-1].get("reporting_period") if rows else None,
        "actual_field": actual or value,
        "source_references": [row.get("record_id") or row.get("id") for row in rows],
        "warnings": [] if len(values) >= 2 else ["insufficient historical observations"],
    }


def financial_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["finance"]
    metrics = [_trend(rows, field, actual=field) for field in ("revenue", "recurring_revenue", "operating_expenses", "payroll_budget", "cash_flow")]
    margin = [_trend(rows, field) for field in ("gross_margin", "operating_margin")]
    variance = [_trend([{"reporting_period": r["reporting_period"], "variance": float(r["actual_revenue"]) - float(r["forecast_revenue"]), "record_id": r["record_id"]}], "variance") for r in rows[-1:]]
    return {"domain": "finance", "currency": data["organization"]["base_currency"], "metrics": metrics + margin, "actual_vs_forecast": variance, "calculation_version": "finance-engine-v1"}


def demand_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    active = [row for row in data["sales"] if row.get("cancellation_status") != "cancelled"]
    weighted = sum(float(row["opportunity_value"]) * float(row["probability"]) for row in active)
    confirmed = sum(float(row["opportunity_value"]) for row in active if row.get("opportunity_stage") == "renewal")
    cancelled = sum(float(row["opportunity_value"]) for row in data["sales"] if row.get("cancellation_status") == "cancelled")
    stages: dict[str, int] = {}
    for row in active:
        stages[row["opportunity_stage"]] = stages.get(row["opportunity_stage"], 0) + 1
    return {
        "active_opportunities": len(active), "weighted_pipeline": round(weighted, 2),
        "confirmed_demand": round(confirmed, 2), "unconfirmed_pipeline": round(weighted - confirmed, 2),
        "cancelled_demand": round(cancelled, 2), "stage_distribution": stages,
        "conversion_rate": round(sum(float(row["probability"]) for row in active) / len(active), 4) if active else None,
        "evidence": [row["record_id"] for row in data["sales"]],
        "calculation_version": "demand-engine-v1",
    }


def project_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["projects"]
    delayed = [row for row in rows if row.get("project_status") == "delayed"]
    cancelled = [row for row in rows if row.get("cancellation_reason")]
    exposure = sum(float(row["contract_value"]) for row in delayed + cancelled)
    demand_by_skill: dict[str, float] = {}
    for row in rows:
        if not row.get("cancellation_reason"):
            skill = row["required_skill_family"]
            demand_by_skill[skill] = demand_by_skill.get(skill, 0) + float(row["required_capacity"])
    return {
        "project_count": len(rows), "delayed_count": len(delayed), "cancelled_count": len(cancelled),
        "delayed_percentage": round(len(delayed) / len(rows) * 100, 2) if rows else None,
        "delayed_revenue_exposure": round(exposure, 2), "skill_demand": demand_by_skill,
        "evidence": [row["record_id"] for row in rows], "calculation_version": "project-engine-v1",
    }


def workforce_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    latest_period = data["workforce"][-1]["reporting_period"]
    rows = [row for row in data["workforce"] if row["reporting_period"] == latest_period]
    by_skill = []
    for row in rows:
        learning = next((item for item in data["learning"] if item["reporting_period"] == latest_period and item["skill_family"] == row["skill_family"]), None)
        demand = float(learning["future_skill_demand"]) if learning else float(row["allocated_capacity"])
        gap = round(demand - float(row["available_capacity"]), 2)
        by_skill.append({"skill_family": row["skill_family"], "business_unit_id": row["business_unit_id"], "period": latest_period, "available_capacity": row["available_capacity"], "allocated_capacity": row["allocated_capacity"], "demand": demand, "gap": gap, "surplus": max(0, -gap), "utilization_rate": row["utilization_rate"], "training_capacity": learning["training_capacity"] if learning else None, "reskilling_feasible": bool(learning and learning["training_capacity"] > 0)})
    return {"reporting_period": latest_period, "skills": by_skill, "aggregate_shortage": round(sum(max(0, item["gap"]) for item in by_skill), 2), "aggregate_surplus": round(sum(item["surplus"] for item in by_skill), 2), "unit": "capacity units", "calculation_version": "workforce-engine-v1"}


def operations_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    def summary(domain: str, fields: tuple[str, ...]) -> dict[str, Any]:
        rows = data[domain]
        return {"domain": domain, "metrics": [_trend(rows, field) for field in fields], "evidence": [row["record_id"] for row in rows]}
    return {
        "ai_transformation": summary("ai_transformation", ("automation_adoption", "productivity_change", "quality_score", "exception_rate", "operating_cost")),
        "cloud": summary("cloud", ("total_cost", "gpu_cost", "gpu_utilization", "compute_utilization")),
        "facilities": summary("facilities", ("energy_cost", "maintenance_cost", "vendor_cost", "capacity_utilization")),
        "calculation_version": "operations-engine-v1",
    }


def anomalies(data: dict[str, Any], threshold: float = 10.0) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for domain, metric in (("finance", "revenue"), ("finance", "operating_expenses"), ("cloud", "total_cost"), ("cloud", "gpu_cost")):
        rows = data[domain]
        values = [float(row[metric]) for row in rows]
        if len(values) < 3:
            continue
        previous, current = values[-2], values[-1]
        change = _pct(current, previous)
        if change is not None and abs(change) >= threshold:
            findings.append({"anomaly_id": f"anomaly:{domain}:{metric}:{rows[-1]['reporting_period']}", "metric": metric, "business_unit_id": rows[-1].get("business_unit_id"), "reporting_period": rows[-1]["reporting_period"], "observed_value": current, "expected_value": previous, "deviation": round(current - previous, 4), "severity": "high" if abs(change) >= threshold * 2 else "medium", "detection_method": "month-over-month percentage change", "supporting_source_references": [rows[-2]["record_id"], rows[-1]["record_id"]], "explanation": f"{metric} changed {change}% from the prior period.", "confidence": 0.8, "investigation_required": abs(change) >= threshold * 2})
    return findings


def forecast_metric(data: dict[str, Any], domain: str, metric: str, horizon_days: int, *, group_field: str | None = None, group_value: str | None = None) -> dict[str, Any]:
    rows = data.get(domain, [])
    if group_field and group_value:
        rows = [row for row in rows if row.get(group_field) == group_value]
    values = [float(row[metric]) for row in rows if row.get(metric) is not None]
    if len(values) < 3:
        return {"status": "insufficient_data", "metric": metric, "horizon_days": horizon_days, "observations": len(values), "uncertainty": "At least three observations are required."}
    recent = values[-min(3, len(values)):]
    slope = (recent[-1] - recent[0]) / max(1, len(recent) - 1)
    steps = HORIZONS.get(horizon_days, max(1, round(horizon_days / 30)))
    value = max(0.0, recent[-1] + slope * steps)
    residuals = [values[i] - (values[i - 1] if i else values[i]) for i in range(1, len(values))]
    deviation = math.sqrt(sum(item * item for item in residuals) / len(residuals)) if residuals else 0
    margin = deviation * math.sqrt(steps)
    return {"status": "forecast", "metric": metric, "business_unit_id": group_value if group_field == "business_unit_id" else None, "forecast_horizon_days": horizon_days, "forecast_value": round(value, 4), "lower_bound": round(max(0, value - margin), 4), "upper_bound": round(value + margin, 4), "model": "three-point trend baseline", "training_period": [rows[0].get("reporting_period"), rows[-1].get("reporting_period")], "observations": len(values), "error_metrics": {"historical_step_rmse": round(deviation, 4)}, "uncertainty": "Bounds use historical one-step residual dispersion; they are not statistical confidence intervals.", "source_references": [row.get("record_id") for row in rows], "calculated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def forecast_suite(data: dict[str, Any], horizon_days: int = 90) -> list[dict[str, Any]]:
    requests = [("finance", "revenue"), ("finance", "operating_expenses"), ("cloud", "total_cost")]
    return [forecast_metric(data, domain, metric, horizon_days) for domain, metric in requests]


def backtest_revenue(data: dict[str, Any]) -> dict[str, Any]:
    values = [float(row["revenue"]) for row in data["finance"]]
    if len(values) < 6:
        return {"status": "insufficient_data", "reason": "At least six observations are required."}
    actual = values[3:]
    predicted = values[2:-1]
    errors = [a - p for a, p in zip(actual, predicted)]
    mae = sum(abs(item) for item in errors) / len(errors)
    rmse = math.sqrt(sum(item * item for item in errors) / len(errors))
    return {"status": "evaluated", "model": "one-step naive baseline", "evaluation_periods": len(errors), "mae": round(mae, 4), "rmse": round(rmse, 4), "baseline": "prior observed month", "leakage_control": "each prediction uses only observations before its target period"}


def business_signals(data: dict[str, Any], threshold: float = 10.0) -> list[dict[str, Any]]:
    found = anomalies(data, threshold)
    signals = []
    for item in found:
        mapping = {("finance", "revenue"): ("REVENUE_DECLINE", "Revenue change detected"), ("finance", "operating_expenses"): ("OPERATING_COST_INCREASE", "Operating cost change detected"), ("cloud", "total_cost"): ("CLOUD_COST_INCREASE", "Cloud cost change detected"), ("cloud", "gpu_cost"): ("CLOUD_COST_INCREASE", "GPU cost change detected")}
        key = ("finance" if item["metric"] in {"revenue", "operating_expenses"} else "cloud", item["metric"])
        event_type, title = mapping[key]
        signals.append({"signal_id": f"signal:{uuid.uuid5(uuid.NAMESPACE_URL, item['anomaly_id'])}", "organization_id": data["organization"]["organization_id"], "business_unit_id": item["business_unit_id"], "event_type": event_type, "title": title, "description": item["explanation"], "severity": item["severity"], "detected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reporting_period": item["reporting_period"], "affected_metrics": [item["metric"]], "observed_values": {"observed": item["observed_value"]}, "comparison_values": {"expected": item["expected_value"]}, "supporting_evidence_ids": item["supporting_source_references"], "source_references": item["supporting_source_references"], "anomaly_ids": [item["anomaly_id"]], "forecast_references": [], "confidence": item["confidence"], "investigation_required": item["investigation_required"], "recommended_investigation_categories": ["finance", "operations"] if event_type != "CLOUD_COST_INCREASE" else ["infrastructure", "finance"], "missing_information": ["validated external or enterprise source confirmation"], "status": "open"})
    return signals
