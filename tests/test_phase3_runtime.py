import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

from app.agent_runtime import build_agent_runtime
from app.main import app


client = TestClient(app)


def test_phase3_catalog_contains_specialists_and_registered_tools():
    catalog = client.get("/api/agents").json()
    names = {agent["name"] for agent in catalog["agents"]}
    assert "Sales and Demand Intelligence Agent" in names
    assert "AI Transformation Intelligence Agent" in names
    assert "Forecast and Risk Intelligence Agent" in names
    tools = {tool["name"] for tool in client.get("/api/tools").json()}
    assert {"sales_demand_analysis", "ai_transformation_analysis", "forecast_risk_analysis"} <= tools


def test_event_specific_investigations_select_different_bounded_paths():
    revenue = client.post("/api/investigate", json={"event_type": "revenue_decline", "budget": 6})
    ai = client.post("/api/investigate", json={"event_type": "ai_transformation", "budget": 6})
    combined = client.post("/api/investigate", json={"event_type": "combined_business_stress", "budget": 6})
    assert revenue.status_code == ai.status_code == combined.status_code == 200
    assert revenue.json()["investigation_status"] == "complete"
    assert ai.json()["investigation_status"] == "complete"
    assert revenue.json()["agent_trace"] != ai.json()["agent_trace"]
    assert "employee_id" not in str(ai.json()).lower()


def test_runtime_tool_permissions_and_dependency_contracts():
    runtime = build_agent_runtime()
    try:
        runtime.registry.invoke("finance_analysis", {}, permissions=())
    except PermissionError as exc:
        assert "read:investigation" in str(exc)
    else:
        raise AssertionError("unapproved tool invocation was accepted")
    spec = runtime.registry.get("capacity_analysis")
    assert spec.dependencies == ("project_analysis",)
