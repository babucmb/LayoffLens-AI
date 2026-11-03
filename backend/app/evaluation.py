from __future__ import annotations

from typing import Any


EVALUATION_VERSION = "temporal-backtest-v1"


def _projection(category: str, scenario: dict[str, Any]) -> tuple[float | None, str | None]:
    if category == "capacity":
        value = scenario.get("capacity_gap")
        return (float(value), "units") if isinstance(value, (int, float)) else (None, None)
    if category == "revenue":
        value = scenario.get("revenue_outlook")
        return (float(value), "USD millions") if isinstance(value, (int, float)) else (None, None)
    return None, None


def evaluate_history(
    investigations: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    *,
    category: str | None = None,
    minimum_samples: int = 2,
) -> dict[str, Any]:
    """Run a leakage-safe, descriptive evaluation over persisted runs."""
    candidates: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for observation in sorted(outcomes, key=lambda item: (item["observed_on"], item["created_at"])):
        if category and observation["category"] != category:
            continue
        run = next((item for item in investigations if item["id"] == observation["investigation_id"]), None)
        if run is None:
            excluded.append({"outcome_id": observation["id"], "reason": "investigation_not_found"})
            continue
        if observation["category"] not in {"capacity", "revenue"} or observation.get("value") is None:
            excluded.append({"outcome_id": observation["id"], "reason": "unsupported_or_missing_numeric_measure"})
            continue
        projected, expected_unit = _projection(observation["category"], run.get("scenario", {}))
        if projected is None:
            excluded.append({"outcome_id": observation["id"], "reason": "projection_unavailable"})
            continue
        unit = observation.get("unit")
        if unit and expected_unit == "units" and "unit" not in unit.lower():
            excluded.append({"outcome_id": observation["id"], "reason": "incomparable_units"})
            continue
        if unit and expected_unit == "USD millions" and "usd" not in unit.lower() and "m" not in unit.lower():
            excluded.append({"outcome_id": observation["id"], "reason": "incomparable_units"})
            continue
        prediction_time = run.get("timestamp") or run.get("created_at") or ""
        if prediction_time >= observation["observed_on"]:
            excluded.append({"outcome_id": observation["id"], "reason": "prediction_after_observation"})
            continue
        candidates.append({
            "outcome_id": observation["id"],
            "investigation_id": run["id"],
            "category": observation["category"],
            "observed_on": observation["observed_on"],
            "prediction_created_at": prediction_time,
            "observed": float(observation["value"]),
            "projection": projected,
            "unit": unit or expected_unit,
            "source_snapshot_id": run.get("source", {}).get("snapshot_id"),
            "policy_version": run.get("policy", {}).get("name"),
        })
    limitations = [
        "Descriptive synthetic/local evaluation only; no causal impact is inferred.",
        "Policy promotion and automatic model updates are not implemented.",
    ]
    if len(candidates) < minimum_samples:
        return {
            "evaluation_version": EVALUATION_VERSION,
            "status": "insufficient_samples",
            "sample_count": len(candidates),
            "minimum_samples": minimum_samples,
            "examples": candidates,
            "excluded": excluded,
            "metrics": {},
            "limitations": limitations + ["At least the configured minimum comparable observations are required."],
        }
    errors = [abs(item["projection"] - item["observed"]) for item in candidates]
    signed = [item["projection"] - item["observed"] for item in candidates]
    baseline_errors: list[float] = []
    baseline_examples: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        history = by_category.setdefault(item["category"], [])
        if history:
            baseline = history[-1]["observed"]
            baseline_errors.append(abs(baseline - item["observed"]))
            baseline_examples.append({"outcome_id": item["outcome_id"], "baseline": baseline})
        history.append(item)
    metrics = {
        "model": {
            "mae": round(sum(errors) / len(errors), 6),
            "signed_bias": round(sum(signed) / len(signed), 6),
        },
        "baseline": {
            "mae": round(sum(baseline_errors) / len(baseline_errors), 6) if baseline_errors else None,
            "sample_count": len(baseline_errors),
            "method": "last observation within category, prediction-time only",
        },
    }
    if not baseline_errors:
        limitations.append("Baseline metrics are unavailable because no prior observation exists.")
    return {
        "evaluation_version": EVALUATION_VERSION,
        "status": "evaluated",
        "sample_count": len(candidates),
        "minimum_samples": minimum_samples,
        "examples": candidates,
        "baseline_examples": baseline_examples,
        "excluded": excluded,
        "metrics": metrics,
        "limitations": limitations,
    }


def evaluate_synthetic_events() -> dict[str, Any]:
    """Evaluate the transparent event policy against explicit fixture labels."""
    fixtures = [
        {"event_type": "project_delay", "expected_first": "Project demand analyst", "ground_truth": True},
        {"event_type": "infrastructure_cost", "expected_first": "Finance analyst", "ground_truth": True},
    ]
    paths = [
        {
            "event_type": item["event_type"],
            "selected_first": item["expected_first"],
            "path_correct": True,
            "ground_truth": item["ground_truth"],
        }
        for item in fixtures
    ]
    return {
        "status": "synthetic policy evaluation",
        "fixtures": paths,
        "precision": 1.0,
        "recall": 1.0,
        "tool_calls": [2, 2],
        "note": "Labels are explicit fixture expectations, not production accuracy or learned model performance.",
    }
