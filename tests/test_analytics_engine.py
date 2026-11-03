import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

from app.analytics_engine import (
    backtest_revenue,
    business_signals,
    demand_intelligence,
    financial_intelligence,
    forecast_metric,
    project_intelligence,
    workforce_intelligence,
)
from app.enterprise_data import build_enterprise_dataset
from app.main import app


DATA = build_enterprise_dataset()
client = TestClient(app)


def test_finance_demand_projects_and_workforce_are_reproducible():
    finance = financial_intelligence(DATA)
    assert finance["currency"] == "USD"
    assert {item["metric"] for item in finance["metrics"]} >= {"revenue", "operating_expenses", "operating_margin"}
    demand = demand_intelligence(DATA)
    assert demand["weighted_pipeline"] > demand["confirmed_demand"]
    assert demand["cancelled_demand"] > 0
    projects = project_intelligence(DATA)
    assert projects["delayed_count"] == 2
    workforce = workforce_intelligence(DATA)
    assert workforce["unit"] == "capacity units"
    assert workforce["skills"]
    assert "employee" not in str(workforce).lower()


def test_forecast_has_explicit_bounds_and_insufficient_data_status():
    result = forecast_metric(DATA, "finance", "revenue", 90)
    assert result["status"] == "forecast"
    assert result["lower_bound"] <= result["forecast_value"] <= result["upper_bound"]
    assert "not statistical confidence" in result["uncertainty"]
    short = forecast_metric({"finance": [{"revenue": 1}]}, "finance", "revenue", 90)
    assert short["status"] == "insufficient_data"


def test_signals_include_evidence_and_recommended_categories():
    signals = business_signals(DATA, threshold=1)
    assert signals
    assert all(item["signal_id"] and item["supporting_evidence_ids"] for item in signals)
    assert all(item["recommended_investigation_categories"] for item in signals)
    assert backtest_revenue(DATA)["status"] == "evaluated"


def test_phase_two_api_endpoints_and_validation():
    assert client.get("/api/analytics/finance").status_code == 200
    assert client.get("/api/analytics/demand").json()["cancelled_demand"] > 0
    assert client.get("/api/analytics/projects").json()["delayed_count"] == 2
    assert client.get("/api/analytics/workforce").json()["skills"]
    assert client.get("/api/analytics/forecasts?horizon_days=365").status_code == 200
    assert client.get("/api/analytics/forecasts?horizon_days=45").status_code == 422
    generated = client.post("/api/signals/generate", json={"threshold": 1}).json()
    assert generated["status"] == "generated"
    assert generated["count"] == len(client.get("/api/signals?threshold=1").json())
