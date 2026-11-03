from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schemas import ScenarioInput


def calculate_scenario(
    data: dict[str, Any],
    scenario: ScenarioInput,
    *,
    finance_result: dict[str, Any] | None = None,
    project_result: dict[str, Any] | None = None,
    capacity_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weighted_pipeline = float(project_result["weighted_pipeline"]) if project_result else sum(float(p["weighted"]) for p in data["projects"])
    adjusted_pipeline = weighted_pipeline * scenario.conversion * (1 - 0.06 * scenario.hiring_delay)
    revenue_base = float(finance_result["revenue"]) if finance_result else float(data["finance"][-1]["revenue"])
    revenue = adjusted_pipeline + revenue_base * 0.55
    infra = (float(data["investment"]["ai_spend"]) + float(data["investment"]["gpu_spend"])) * (1 + scenario.infra_change)
    gaps: list[dict[str, Any]] = []
    capacity_rows = capacity_result.get("gap_by_skill", []) if capacity_result else []
    capacity_by_skill = {row["skill"]: row for row in capacity_rows}
    for row in data["capacity"]:
        delay_demand = scenario.delay_months * 1.2 if row["skill"] in ("Cloud", "Data") else 0
        hiring_capacity = 0 if scenario.hiring_delay >= 1 else (
            sum(h["seats"] for h in data["hiring"] if h["skill"] == row["skill"]) * 0.5
        )
        mobility_offset = scenario.mobility if row["skill"] == "Cloud" else 0
        upstream = capacity_by_skill.get(row["skill"], {})
        demand = float(upstream.get("demand", row["demand"])) + delay_demand
        capacity = float(upstream.get("capacity", row["capacity"])) + hiring_capacity + mobility_offset
        gaps.append({"skill": row["skill"], "gap": round(demand - capacity, 1), "capacity": round(capacity, 1), "demand": round(demand, 1)})
    total_gap = round(sum(max(0, item["gap"]) for item in gaps), 1)
    confidence = max(0.52, min(0.95, 0.83 - scenario.delay_months * 0.04 - abs(scenario.infra_change) * 0.08 - scenario.hiring_delay * 0.02))
    return {
        "revenue_outlook": round(max(0, revenue), 2),
        "weighted_pipeline": round(max(0, adjusted_pipeline), 2),
        "infrastructure_spend": round(max(0, infra), 2),
        "capacity_gap": total_gap,
        "gap_by_skill": gaps,
        "confidence": round(confidence, 2),
        "formula": "pipeline = weighted value x conversion x (1 - 6% x hiring delay); gap = demand - capacity - hiring capacity - mobility",
        "inputs_consumed": [
            name for name, value in (
                ("finance_analysis", finance_result),
                ("project_analysis", project_result),
                ("capacity_analysis", capacity_result),
            ) if value is not None
        ],
        "assumptions": {
            **scenario.model_dump(),
            "finance_revenue_source": "finance_analysis" if finance_result else "source_data",
            "pipeline_source": "project_analysis" if project_result else "source_data",
            "capacity_source": "capacity_analysis" if capacity_result else "source_data",
        },
    }


def finance_analysis(data: dict[str, Any]) -> dict[str, Any]:
    latest = data["finance"][-1]
    variance = round(float(latest["revenue"]) - float(latest["budget"]), 2)
    return {"revenue": latest["revenue"], "budget": latest["budget"], "variance": variance, "opex": latest["opex"], "pressure": "high" if variance < 0 else "normal", "evidence": [latest["id"]]}


def project_analysis(data: dict[str, Any]) -> dict[str, Any]:
    flagged = [p for p in data["projects"] if p["status"] != "on track"]
    return {"flagged_projects": len(flagged), "weighted_pipeline": round(sum(float(p["weighted"]) for p in data["projects"]), 2), "delayed_skills": sorted({p["skill"] for p in flagged}), "evidence": [p["id"] for p in flagged]}


def capacity_analysis(data: dict[str, Any], scenario: ScenarioInput) -> dict[str, Any]:
    rows = [
        {
            "skill": row["skill"],
            "gap": round(float(row["demand"]) - float(row["capacity"]), 1),
            "capacity": round(float(row["capacity"]), 1),
            "demand": round(float(row["demand"]), 1),
        }
        for row in data["capacity"]
    ]
    return {
        "capacity_gap": round(sum(max(0, item["gap"]) for item in rows), 1),
        "gap_by_skill": rows,
        "evidence": [f"capacity:{r['skill']}" for r in data["capacity"]],
        "scenario_inputs": scenario.model_dump(),
    }


def action_plan(
    data: dict[str, Any],
    scenario: ScenarioInput,
    *,
    scenario_result: dict[str, Any] | None = None,
    finance_result: dict[str, Any] | None = None,
    project_result: dict[str, Any] | None = None,
    capacity_result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    baseline = scenario_result or calculate_scenario(
        data,
        scenario,
        finance_result=finance_result,
        project_result=project_result,
        capacity_result=capacity_result,
    )
    mobility_units = min(2.0, max(0, baseline["capacity_gap"]))
    capacity_gaps = {row["skill"]: float(row["gap"]) for row in baseline.get("gap_by_skill", [])}
    finance_pressure = finance_result.get("pressure") if finance_result else finance_analysis(data).get("pressure")
    project_constraints = project_result.get("delayed_skills", []) if project_result else project_analysis(data).get("delayed_skills", [])
    actions = [
        {"id": "mobility", "name": "Internal mobility", "condition": "Cloud aggregate gap is positive", "eligible": capacity_gaps.get("Cloud", 0) > 0, "cost": round(mobility_units * 0.09, 2), "cost_unit": "USD millions", "benefit": f"Offsets up to {mobility_units:.1f} Cloud capacity units", "time_to_effect": "4 weeks", "uncertainty": "Illustrative training and transition cost", "approval": "Workforce council", "evidence": ["capacity:Cloud"], "inputs_consumed": ["scenario_result", "capacity_analysis"] if capacity_result else ["scenario_result"]},
        {"id": "reskill", "name": "Reskilling sprint", "condition": "Cloud or Data gap is positive", "eligible": any(capacity_gaps.get(skill, 0) > 0 for skill in ("Cloud", "Data")), "cost": 0.32, "cost_unit": "USD millions", "benefit": "Builds cross-skill capacity over 8-10 weeks", "time_to_effect": "8-10 weeks", "uncertainty": "Outcome depends on completion and delivery load", "approval": "L&D + business owner", "evidence": ["capacity:Cloud", "capacity:Data"], "inputs_consumed": ["scenario_result", "capacity_analysis"] if capacity_result else ["scenario_result"]},
        {"id": "hiring", "name": "Hiring timing review", "condition": "Approved joins exist", "eligible": bool(data["hiring"]), "cost": 0.0, "cost_unit": "USD millions", "benefit": f"Reviews timing of {sum(h['seats'] for h in data['hiring'])} approved seats", "time_to_effect": "1 week", "uncertainty": "May slow readiness if demand returns", "approval": "Human hiring committee", "evidence": [h["id"] for h in data["hiring"]], "inputs_consumed": ["source_data:hiring"]},
        {"id": "infra", "name": "Infrastructure schedule review", "condition": "AI/GPU spend is present", "eligible": bool(data["investment"].get("gpu_spend")), "cost": round(float(data["investment"]["gpu_spend"]) * 0.05, 2), "cost_unit": "USD millions", "benefit": "Tests whether GPU schedule matches measured adoption", "time_to_effect": "2 weeks", "uncertainty": "Could delay experiments", "approval": "Platform finance", "evidence": ["investment:ai-2026-10"], "inputs_consumed": ["finance_analysis"] if finance_result else ["source_data:investment"]},
    ]
    for action in actions:
        action["assumptions"] = {
            "finance_pressure": finance_pressure,
            "delayed_skills": project_constraints,
            "synthetic_estimate": True,
        }
    return actions


CALCULATION_VERSION = "scenario-evaluation-v1"


def _scenario_record(
    scenario_id: str,
    scenario_type: str,
    result: dict[str, Any],
    *,
    estimated_cost: float | None,
    gross_savings: float | None,
    feasibility: str,
    explanation: str,
    assumptions: list[str],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    limitations = limitations or []
    status = "evaluated" if feasibility != "insufficient_data" else "insufficient_data"
    net = None if estimated_cost is None or gross_savings is None else round(gross_savings - estimated_cost, 2)
    return {
        "scenario_id": scenario_id,
        "scenario_type": scenario_type,
        "calculation_version": CALCULATION_VERSION,
        "units": "USD millions; capacity in aggregate units",
        "time_horizon": "illustrative 12-month financial view; 0-3 month capacity view",
        "estimated_cost": estimated_cost,
        "gross_savings": gross_savings,
        "net_savings": net,
        "feasibility": feasibility,
        "evaluation_status": status,
        "explanation": explanation,
        "assumptions": assumptions,
        "limitations": limitations,
        "result": result,
    }


def evaluate_scenarios(
    data: dict[str, Any],
    scenario: ScenarioInput,
    *,
    finance_result: dict[str, Any] | None = None,
    project_result: dict[str, Any] | None = None,
    capacity_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate mutually exclusive aggregate interventions with transparent formulas."""
    baseline = calculate_scenario(data, ScenarioInput(), finance_result=finance_result, project_result=project_result, capacity_result=capacity_result)
    downside = calculate_scenario(
        data,
        ScenarioInput(delay_months=2, conversion=0.68, infra_change=0.25, hiring_delay=1, mobility=0),
        finance_result=finance_result,
        project_result=project_result,
        capacity_result=capacity_result,
    )
    intervention = calculate_scenario(data, scenario, finance_result=finance_result, project_result=project_result, capacity_result=capacity_result)
    finance_available = finance_result is not None
    latest_opex = float(finance_result["opex"]) if finance_available else 0.0
    seats = sum(float(item["seats"]) for item in data.get("hiring", []))
    pipeline = float((project_result or project_analysis(data))["weighted_pipeline"])
    gaps = float(intervention["capacity_gap"])
    alternatives = [
        _scenario_record(
            "spending-reduction", "alternative", intervention, estimated_cost=0.0,
            gross_savings=round(latest_opex * 0.05, 2) if finance_available else None,
            feasibility="feasible" if finance_available and latest_opex > 0 else "insufficient_data",
            explanation="Illustrative discretionary-spend reduction equals 5% of latest monthly opex; it is not added to other alternatives.",
            assumptions=["5% of latest opex is discretionary", "Savings are illustrative and not validated"],
            limitations=["No finance analysis was available", "No procurement or contract data is available"] if not finance_available else ["No procurement or contract data is available"],
        ),
        _scenario_record(
            "project-reprioritization", "alternative", intervention, estimated_cost=round(pipeline * 0.01, 2),
            gross_savings=round(pipeline * 0.08, 2),
            feasibility="feasible" if pipeline > 0 and project_result is not None else "insufficient_data",
            explanation="Deferral is modeled as 8% of weighted pipeline less a 1% transition cost.",
            assumptions=["Weighted pipeline is the available project proxy", "Deferral does not imply contract cancellation"],
            limitations=[] if project_result is not None else ["Project analysis was not available"],
        ),
        _scenario_record(
            "hiring-adjustment", "alternative", intervention, estimated_cost=0.0,
            gross_savings=round(seats * 0.06, 2),
            feasibility="feasible" if seats > 0 else "insufficient_data",
            explanation="Timing review models 0.06 USD million per approved seat as an illustrative avoided near-term cost.",
            assumptions=["Approved seats are available for timing review", "No employment decision is automated"],
            limitations=["Hiring costs and contractual constraints are unknown"],
        ),
        _scenario_record(
            "internal-redeployment", "alternative", intervention, estimated_cost=round(min(2.0, max(0, gaps)) * 0.09, 2),
            gross_savings=round(min(2.0, max(0, gaps)) * 0.18, 2) if gaps > 0 else 0.0,
            feasibility="feasible" if gaps > 0 and capacity_result is not None else "insufficient_data",
            explanation="Redeployment models two or fewer aggregate capacity units at 0.09 cost and 0.18 avoided-gap value per unit.",
            assumptions=["Positive aggregate gap can be addressed through mobility", "Skills are transferable after human review"],
            limitations=[] if capacity_result is not None else ["Capacity analysis was not available"],
        ),
    ]
    records = [
        _scenario_record("baseline", "baseline", baseline, estimated_cost=None, gross_savings=None, feasibility="feasible", explanation="Current seeded operating picture without intervention.", assumptions=["Synthetic source records are representative for the demo"], limitations=["Not a forecast"]),
        _scenario_record("downside", "downside", downside, estimated_cost=None, gross_savings=None, feasibility="feasible", explanation="Defined downside assumptions for comparison only.", assumptions=["Conversion 68%, two-month delay, 25% infrastructure change, one-month hiring delay"], limitations=["Not a calibrated confidence interval"]),
        _scenario_record("intervention", "intervention", intervention, estimated_cost=None, gross_savings=None, feasibility="feasible", explanation="User-selected aggregate scenario inputs.", assumptions=[f"{key}={value}" for key, value in scenario.model_dump().items()], limitations=["Illustrative estimate"]),
        *alternatives,
    ]
    evaluated = [item for item in records if item["evaluation_status"] == "evaluated" and item["scenario_type"] == "alternative"]
    reversibility = {
        "spending-reduction": 0.8,
        "project-reprioritization": 0.6,
        "hiring-adjustment": 0.9,
        "internal-redeployment": 0.7,
    }
    weights = {"feasibility": 0.35, "net_financial_impact": 0.35, "evidence_completeness": 0.10, "reversibility": 0.20}
    for item in evaluated:
        normalized_net = max(0.0, min(1.0, (float(item["net_savings"] or 0.0) + 1.0) / 2.0))
        components = {
            "feasibility": 1.0 if item["feasibility"] == "feasible" else 0.0,
            "net_financial_impact": normalized_net,
            "evidence_completeness": 1.0 if not item["limitations"] else 0.0,
            "reversibility": reversibility[item["scenario_id"]],
        }
        item["ranking_components"] = components
        item["comparison_score"] = round(sum(weights[key] * components[key] for key in weights), 3)
    ranked = sorted(evaluated, key=lambda item: item["comparison_score"], reverse=True)
    return {
        "calculation_version": CALCULATION_VERSION,
        "scenarios": records,
        "ranking": [item["scenario_id"] for item in ranked],
        "ranking_criteria": {
            **weights,
        },
        "ranking_explanation": "Only evaluated alternatives are ranked; weights are explicit and scores are not an AI-generated decision.",
        "double_counting_warning": "Alternatives are mutually exclusive comparison cases; savings must not be summed.",
        "inputs_consumed": [name for name, value in (("finance_analysis", finance_result), ("project_analysis", project_result), ("capacity_analysis", capacity_result)) if value is not None],
    }


def sensitivity_analysis(data: dict[str, Any], scenario: ScenarioInput) -> dict[str, Any]:
    bounds = {
        "delay_months": (0.0, 4.0),
        "conversion": (0.5, 1.0),
        "infra_change": (-0.2, 0.6),
        "hiring_delay": (0.0, 3.0),
        "mobility": (0.0, 8.0),
    }
    results: list[dict[str, Any]] = []
    for parameter, (low, high) in bounds.items():
        values = [low, high]
        outcomes = []
        for value in values:
            adjusted = scenario.model_copy(update={parameter: value})
            result = calculate_scenario(data, adjusted)
            outcomes.append({"value": value, "revenue_outlook": result["revenue_outlook"], "capacity_gap": result["capacity_gap"], "infrastructure_spend": result["infrastructure_spend"]})
        results.append({"parameter": parameter, "bounds": {"low": low, "high": high}, "outcomes": outcomes, "range_effect": {"revenue_outlook": round(outcomes[1]["revenue_outlook"] - outcomes[0]["revenue_outlook"], 2), "capacity_gap": round(outcomes[1]["capacity_gap"] - outcomes[0]["capacity_gap"], 2), "infrastructure_spend": round(outcomes[1]["infrastructure_spend"] - outcomes[0]["infrastructure_spend"], 2)}})
    greatest = max(results, key=lambda item: abs(item["range_effect"]["revenue_outlook"]) + abs(item["range_effect"]["capacity_gap"]))
    return {"calculation_version": CALCULATION_VERSION, "bounds": bounds, "results": results, "most_sensitive_parameter": greatest["parameter"], "method": "endpoint analysis over declared deterministic bounds; not a confidence interval"}


def compare_observation_to_projection(observation: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    if observation.get("value") is None:
        return {"status": "insufficient_data", "observed_value": None, "projected_value": None, "difference": None, "explanation": "Observation has no numeric value."}
    key_by_category = {"capacity": "capacity_gap", "revenue": "revenue_outlook"}
    key = key_by_category.get(observation.get("category"))
    if key is None or key not in scenario:
        return {"status": "not_comparable", "observed_value": observation["value"], "projected_value": None, "difference": None, "explanation": "Category has no comparable projection in the scenario result."}
    projected = float(scenario[key])
    observed = float(observation["value"])
    return {"status": "comparable", "observed_value": observed, "projected_value": projected, "difference": round(observed - projected, 2), "explanation": "Difference is descriptive only; it is not evidence of causal impact. Timing, units, and intervention attribution require human review."}


def freshness(data: dict[str, Any]) -> dict[str, Any]:
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"status": "synthetic_seed", "checked_at": checked, "warning": "Seeded demo records do not include source ingestion timestamps."}


def mae(actual: list[float], forecast: list[float]) -> float:
    pairs = [(a, f) for a, f in zip(actual, forecast) if a is not None and f is not None]
    return round(sum(abs(a - f) for a, f in pairs) / len(pairs), 3) if pairs else 0.0


def wape(actual: list[float], forecast: list[float]) -> float:
    pairs = [(a, f) for a, f in zip(actual, forecast) if a is not None and f is not None]
    denominator = sum(abs(a) for a, _ in pairs)
    return round(sum(abs(a - f) for a, f in pairs) / denominator, 4) if denominator else 0.0
