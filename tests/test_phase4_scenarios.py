import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_canonical_scenarios_are_reproducible_and_persisted():
    payload = {"scenario_type": "downside", "horizon_days": 90}
    first = client.post("/api/scenarios/v2", json=payload)
    second = client.post("/api/scenarios/v2", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["financial_results"] == second.json()["financial_results"]
    assert first.json()["scenario_id"] != second.json()["scenario_id"]
    assert client.get(f"/api/scenarios/{first.json()['scenario_id']}").status_code == 200
    assert any(item["scenario_id"] == first.json()["scenario_id"] for item in client.get("/api/scenarios/history").json())


def test_interventions_constraints_and_mutually_exclusive_savings():
    interventions = client.get("/api/scenario-interventions").json()
    assert len(interventions) >= 5
    assert all(item["human_approval_required"] for item in interventions)
    result = client.post("/api/scenarios/v2", json={"scenario_type": "alternative", "intervention_id": "internal-mobility", "constraints": {"max_budget": 0.01}})
    assert result.status_code == 200
    assert result.json()["operational_results"]["feasibility"] == "infeasible"
    assert "must not be added together" in " ".join(result.json()["limitations"])


def test_sensitivity_and_comparison_endpoints():
    sensitivity = client.post("/api/scenarios/sensitivity", json={"scenario_type": "stress", "horizon_days": 180}).json()
    assert sensitivity["results"]
    assert all("absolute_impact" in item and "limitations" in item for item in sensitivity["results"])
    first = client.post("/api/scenarios/v2", json={"scenario_type": "baseline"}).json()
    second = client.post("/api/scenarios/v2", json={"scenario_type": "upside"}).json()
    comparison = client.get(f"/api/scenarios/{first['scenario_id']}/compare/{second['scenario_id']}")
    assert comparison.status_code == 200
    assert "revenue_outlook" in comparison.json()["differences"]


def test_invalid_horizon_is_rejected():
    response = client.post("/api/scenarios/v2", json={"scenario_type": "baseline", "horizon_days": 45})
    assert response.status_code == 422
