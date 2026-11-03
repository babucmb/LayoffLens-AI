from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


CALCULATION_VERSION = "phase4-scenario-v1"
HORIZONS = {30, 90, 180, 365}


def _latest(rows: list[dict[str, Any]], period: str | None = None) -> list[dict[str, Any]]:
    if not rows:
        return []
    period = period or max(row.get("reporting_period", "") for row in rows)
    return [row for row in rows if row.get("reporting_period") == period]


def _base(data: dict[str, Any]) -> dict[str, Any]:
    finance = data.get("finance", [])
    sales = [row for row in data.get("sales", []) if row.get("cancellation_status") != "cancelled"]
    workforce = _latest(data.get("workforce", []))
    cloud = _latest(data.get("cloud", []))
    missing = [domain for domain in ("finance", "sales", "projects", "workforce", "cloud") if not data.get(domain)]
    revenue = float(finance[-1]["actual_revenue"]) if finance else 0.0
    opex = float(finance[-1]["operating_expenses"]) if finance else 0.0
    pipeline = sum(float(row.get("opportunity_value", 0)) * float(row.get("probability", 0)) for row in sales)
    capacity = sum(float(row.get("available_capacity", 0)) for row in workforce)
    demand = sum(float(row.get("future_skill_demand", 0)) for row in data.get("learning", []) if row.get("reporting_period") == (workforce[0].get("reporting_period") if workforce else None))
    if not demand:
        demand = sum(float(row.get("allocated_capacity", 0)) for row in workforce)
    infrastructure = sum(float(row.get("total_cost", 0)) for row in cloud)
    return {
        "revenue": revenue, "opex": opex, "weighted_pipeline": pipeline,
        "capacity": capacity, "demand": demand, "capacity_gap": round(max(0, demand - capacity), 2),
        "infrastructure_spend": infrastructure, "missing_inputs": missing,
        "evidence": [row.get("record_id", row.get("id")) for group in ("finance", "sales", "projects", "workforce", "cloud") for row in data.get(group, [])],
    }


def interventions(data: dict[str, Any]) -> list[dict[str, Any]]:
    base = _base(data)
    gap = base["capacity_gap"]
    has = lambda domain: bool(data.get(domain))
    return [
        {"intervention_id": "internal-mobility", "name": "Internal mobility", "description": "Rebalance aggregate skill-family capacity.", "target_domain": "workforce", "estimated_cost": round(min(2, gap) * .09, 2), "expected_savings": round(min(2, gap) * .18, 2) if gap else 0.0, "operational_impact": {"capacity_units": round(min(2, gap), 2)}, "time_to_effect_days": 30, "dependencies": ["workforce"], "risks": ["Transferability requires human review"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Capacity units are aggregate and transferable only after validation"], "uncertainty": "Illustrative unit economics.", "limitations": [] if has("workforce") else ["Workforce data is missing"], "status": "evaluated" if has("workforce") else "insufficient_data"},
        {"intervention_id": "reskilling", "name": "Reskilling and upskilling", "description": "Use available aggregate training capacity to address skill gaps.", "target_domain": "learning", "estimated_cost": .32, "expected_savings": round(min(2, gap) * .14, 2), "operational_impact": {"capacity_units": round(min(2, gap) * .7, 2)}, "time_to_effect_days": 60, "dependencies": ["workforce", "learning"], "risks": ["Training completion and delivery load"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Training capacity is available"], "uncertainty": "Effectiveness is not statistically calibrated.", "limitations": [] if has("workforce") and has("learning") else ["Workforce or learning data is missing"], "status": "evaluated" if has("workforce") and has("learning") else "insufficient_data"},
        {"intervention_id": "hiring-timing", "name": "Hiring timing adjustment", "description": "Review timing of committed aggregate capacity.", "target_domain": "hiring", "estimated_cost": 0.0, "expected_savings": round(sum(float(row.get("estimated_cost", 0)) for row in data.get("hiring", [])) * .2, 2), "operational_impact": {"capacity_units": 0}, "time_to_effect_days": 14, "dependencies": ["hiring"], "risks": ["Readiness may be delayed"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Commitments can be reviewed"], "uncertainty": "Contractual constraints are unknown.", "limitations": [] if has("hiring") else ["Hiring data is missing"], "status": "evaluated" if has("hiring") else "insufficient_data"},
        {"intervention_id": "project-reprioritization", "name": "Project reprioritization", "description": "Sequence delivery work without treating deferral as realized savings.", "target_domain": "projects", "estimated_cost": round(base["weighted_pipeline"] * .01, 2), "expected_savings": None, "operational_impact": {"delivery_risk": "requires portfolio review"}, "time_to_effect_days": 30, "dependencies": ["projects", "sales"], "risks": ["Customer and delivery commitments"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Deferral is not cancellation"], "uncertainty": "No realized savings are claimed.", "limitations": [] if has("projects") and has("sales") else ["Project or sales data is missing"], "status": "evaluated" if has("projects") and has("sales") else "insufficient_data"},
        {"intervention_id": "infrastructure-optimization", "name": "Cloud and GPU optimization", "description": "Review schedules against measured utilization.", "target_domain": "cloud", "estimated_cost": round(base["infrastructure_spend"] * .05, 2), "expected_savings": round(base["infrastructure_spend"] * .08, 2) if base["infrastructure_spend"] else None, "operational_impact": {"utilization_review": True}, "time_to_effect_days": 30, "dependencies": ["cloud"], "risks": ["May delay experiments"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Some schedule flexibility exists"], "uncertainty": "Savings are illustrative and not validated.", "limitations": [] if has("cloud") else ["Cloud billing data is missing"], "status": "evaluated" if has("cloud") else "insufficient_data"},
        {"intervention_id": "contractor-vendor-optimization", "name": "Contractor and vendor optimization", "description": "Review aggregate external delivery capacity and vendor commitments.", "target_domain": "hiring", "estimated_cost": 0.05, "expected_savings": round(sum(float(row.get("estimated_cost", 0)) for row in data.get("hiring", [])) * .12, 2), "operational_impact": {"capacity_units": 0}, "time_to_effect_days": 45, "dependencies": ["hiring"], "risks": ["Supplier and delivery commitments"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Contracts are reviewable"], "uncertainty": "Contract terms are not present in synthetic data.", "limitations": [] if has("hiring") else ["Hiring data is missing"], "status": "evaluated" if has("hiring") else "insufficient_data"},
        {"intervention_id": "discretionary-spending-review", "name": "Discretionary spending review", "description": "Identify non-essential operating spend for human review.", "target_domain": "finance", "estimated_cost": 0.02, "expected_savings": round(base["opex"] * .015, 2), "operational_impact": {"service_review_required": True}, "time_to_effect_days": 30, "dependencies": ["finance"], "risks": ["Service quality or delivery impact"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Operating expense categories are reviewable"], "uncertainty": "Illustrative percentage, not a budget recommendation.", "limitations": [] if has("finance") else ["Finance data is missing"], "status": "evaluated" if has("finance") else "insufficient_data"},
        {"intervention_id": "investment-reallocation", "name": "Investment reallocation", "description": "Rebalance aggregate investment timing toward committed priorities.", "target_domain": "finance", "estimated_cost": 0.03, "expected_savings": round(base["opex"] * .01, 2), "operational_impact": {"portfolio_review_required": True}, "time_to_effect_days": 60, "dependencies": ["finance", "projects"], "risks": ["Strategic option value may change"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Portfolio commitments can be reviewed"], "uncertainty": "No investment ledger is available.", "limitations": [] if has("finance") and has("projects") else ["Finance or project data is missing"], "status": "evaluated" if has("finance") and has("projects") else "insufficient_data"},
        {"intervention_id": "ai-productivity-investment", "name": "AI productivity investment", "description": "Evaluate aggregate productivity enablement before reducing delivery capacity.", "target_domain": "ai_transformation", "estimated_cost": 0.4, "expected_savings": round(base["opex"] * .02, 2), "operational_impact": {"capacity_units": round(min(1, gap) * .5, 2)}, "time_to_effect_days": 90, "dependencies": ["ai_transformation", "workforce"], "risks": ["Adoption and governance burden"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Use cases pass human governance review"], "uncertainty": "Productivity effect is illustrative.", "limitations": [] if has("ai_transformation") and has("workforce") else ["AI transformation or workforce data is missing"], "status": "evaluated" if has("ai_transformation") and has("workforce") else "insufficient_data"},
        {"intervention_id": "combined-preventive-package", "name": "Combined preventive package", "description": "Evaluate a dependency-checked package; component savings remain mutually exclusive.", "target_domain": "enterprise", "estimated_cost": 0.0, "expected_savings": None, "operational_impact": {"requires_component_selection": True}, "time_to_effect_days": 90, "dependencies": ["finance", "workforce", "projects"], "risks": ["Interactions and double counting"], "reversible": True, "human_approval_required": True, "evidence": base["evidence"], "assumptions": ["Components require separate approval"], "uncertainty": "No additive savings are claimed.", "limitations": ["Select and evaluate components separately"], "status": "evaluated" if has("finance") and has("workforce") and has("projects") else "insufficient_data"},
    ]


def simulate(data: dict[str, Any], scenario_type: str, assumptions: dict[str, float] | None = None, horizon_days: int = 90, intervention_id: str | None = None, constraints: dict[str, float] | None = None) -> dict[str, Any]:
    if horizon_days not in HORIZONS:
        raise ValueError(f"horizon_days must be one of {sorted(HORIZONS)}")
    assumptions = assumptions or {}
    constraints = constraints or {}
    base = _base(data)
    factors = {
        "baseline": {"revenue": 1.0, "opex": 1.0, "pipeline": 1.0, "gap": 1.0},
        "upside": {"revenue": 1.08, "opex": .98, "pipeline": 1.12, "gap": .85},
        "downside": {"revenue": .88, "opex": 1.08, "pipeline": .78, "gap": 1.2},
        "stress": {"revenue": .75, "opex": 1.18, "pipeline": .62, "gap": 1.35},
        "intervention": {"revenue": 1.0, "opex": 1.0, "pipeline": 1.0, "gap": 1.0},
        "alternative": {"revenue": 1.0, "opex": 1.0, "pipeline": 1.0, "gap": 1.0},
    }
    if scenario_type not in factors:
        raise ValueError("Unsupported scenario_type.")
    factor = factors[scenario_type].copy()
    factor["revenue"] *= float(assumptions.get("revenue_factor", 1.0))
    factor["opex"] *= float(assumptions.get("opex_factor", 1.0))
    factor["pipeline"] *= float(assumptions.get("pipeline_factor", 1.0))
    factor["gap"] *= float(assumptions.get("capacity_factor", 1.0))
    selected = None
    if intervention_id:
        selected = next((item for item in interventions(data) if item["intervention_id"] == intervention_id), None)
        if selected is None:
            raise ValueError(f"Unknown intervention_id: {intervention_id}")
        if selected["status"] != "evaluated":
            return {"status": "insufficient_data", "scenario_type": scenario_type, "intervention_id": intervention_id, "limitations": selected["limitations"]}
        factor["gap"] = max(0, factor["gap"] - float(selected["operational_impact"].get("capacity_units", 0)))
    output = {
        "revenue_outlook": round(base["revenue"] * factor["revenue"], 4),
        "weighted_pipeline": round(base["weighted_pipeline"] * factor["pipeline"], 4),
        "operating_expenses": round(base["opex"] * factor["opex"], 4),
        "infrastructure_spend": round(base["infrastructure_spend"] * factor["opex"], 4),
        "capacity_gap": round(base["capacity_gap"] * factor["gap"], 4),
    }
    feasibility = "feasible"
    reasons = []
    if "max_budget" in constraints and selected and float(selected["estimated_cost"]) > constraints["max_budget"]:
        feasibility, reasons = "infeasible", ["estimated_cost exceeds max_budget"]
    if "max_implementation_days" in constraints and selected and selected["time_to_effect_days"] > constraints["max_implementation_days"]:
        feasibility, reasons = "infeasible", ["time_to_effect_days exceeds max_implementation_days"]
    if "min_capacity_coverage" in constraints and base["capacity"] and output["capacity_gap"] > base["capacity"] * (1 - constraints["min_capacity_coverage"]):
        feasibility, reasons = "infeasible", ["capacity coverage constraint is not met"]
    payload = {"scenario_type": scenario_type, "scenario_name": scenario_type.title(), "description": "Deterministic scenario estimate; not a validated prediction.", "assumptions": assumptions, "calculation_version": CALCULATION_VERSION, "forecast_horizon_days": horizon_days, "financial_results": output, "operational_results": {"feasibility": feasibility, "constraint_reasons": reasons}, "workforce_results": {"capacity_gap": output["capacity_gap"], "unit": "aggregate capacity units"}, "evidence_references": base["evidence"], "data_quality": {"status": "insufficient_data" if base["missing_inputs"] else "valid", "missing_inputs": base["missing_inputs"]}, "uncertainty": "Deterministic sensitivity estimate; not a confidence interval.", "limitations": ["Synthetic data", "Mutually exclusive alternatives must not be added together"], "source_snapshot_id": data.get("_source_snapshot_id"), "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "intervention_id": intervention_id}
    payload["scenario_id"] = f"scenario:{uuid.uuid4()}"
    return payload


def sensitivity(data: dict[str, Any], scenario_type: str, base_assumptions: dict[str, float] | None = None) -> dict[str, Any]:
    base_assumptions = base_assumptions or {}
    bounds = {"revenue_factor": (.8, 1.2), "opex_factor": (.9, 1.2), "pipeline_factor": (.7, 1.2), "capacity_factor": (.8, 1.3)}
    results = []
    for parameter, (low, high) in bounds.items():
        low_result = simulate(data, scenario_type, {**base_assumptions, parameter: low})
        high_result = simulate(data, scenario_type, {**base_assumptions, parameter: high})
        low_value, high_value = low_result["financial_results"]["revenue_outlook"], high_result["financial_results"]["revenue_outlook"]
        results.append({"parameter": parameter, "low": low, "high": high, "baseline": simulate(data, scenario_type, base_assumptions)["financial_results"]["revenue_outlook"], "results": [low_value, high_value], "absolute_impact": round(high_value - low_value, 4), "relative_impact": round((high_value - low_value) / abs(low_value), 4) if low_value else None, "units": "USD millions", "method": "deterministic endpoint sensitivity", "interpretation": "Range effect is not a confidence interval.", "limitations": ["No supported probability distribution; Monte Carlo not run."]})
    return {"calculation_version": CALCULATION_VERSION, "scenario_type": scenario_type, "results": results, "most_sensitive_parameter": max(results, key=lambda item: abs(item["absolute_impact"]))["parameter"]}
