import os
import sys
import json
import re
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from app.analytics import action_plan, calculate_scenario as calculate_with_data, capacity_analysis, evaluate_scenarios, mae, sensitivity_analysis, wape
from app.agents import run_investigation, validate_model_tool_request, validate_tool_request
from app.main import DATA, MetaModelClient, ScenarioInput, app, calculate_scenario
from app.orchestration import DeterministicPlanner, InvestigationContext, MetaModelPlanner
from app.sources import FileSourceAdapter, SyntheticSourceAdapter
from app.persistence import Repository
from app.monitor import LocalMonitor, read_monitor_snapshot
from app.evaluation import evaluate_history
from app.agent_runtime import (
    AgentSpec,
    AgentRuntime,
    EnterpriseIntelligenceSupervisor,
    ScriptedModelProvider,
    ToolRegistry,
    ToolSpec,
)
from app.validation import validate_data


client = TestClient(app)


def test_scenario_is_aggregate_and_deterministic():
    result = calculate_scenario(ScenarioInput())
    assert result["capacity_gap"] > 0
    assert result["revenue_outlook"] == calculate_scenario(ScenarioInput())["revenue_outlook"]
    assert "employee" not in str(result).lower()


def test_overview_and_scenarios():
    assert client.get("/api/overview").status_code == 200
    response = client.post("/api/scenarios", json={"delay_months": 2, "conversion": .7, "infra_change": .2, "hiring_delay": 1, "mobility": 2})
    assert response.status_code == 200
    assert response.json()["downside"]["capacity_gap"] >= response.json()["baseline"]["capacity_gap"]
    baseline = response.json()["baseline"]
    changed = client.post("/api/scenarios", json={"delay_months": 0, "conversion": 1, "infra_change": 0, "hiring_delay": 0, "mobility": 8}).json()["intervention"]
    assert changed["capacity_gap"] < baseline["capacity_gap"]
    assert client.post("/api/scenarios", json={"delay_months": 1, "conversion": .7, "infra_change": .2, "hiring_delay": 3, "mobility": 0}).json()["intervention"]["revenue_outlook"] < baseline["revenue_outlook"]


def test_scenario_evaluation_is_transparent_and_reproducible():
    request = {"delay_months": 1, "conversion": .82, "infra_change": .12, "hiring_delay": 0, "mobility": 2}
    first = client.post("/api/scenarios", json=request)
    second = client.post("/api/scenarios", json=request)
    assert first.status_code == second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert first_data["evaluation"] == second_data["evaluation"]
    assert {"baseline", "downside", "intervention"} <= {item["scenario_id"] for item in first_data["evaluation"]["scenarios"]}
    alternatives = [item for item in first_data["evaluation"]["scenarios"] if item["scenario_type"] == "alternative"]
    assert alternatives
    assert all(item["units"] and item["time_horizon"] and item["explanation"] for item in alternatives)
    assert "double_counting_warning" in first_data["evaluation"]
    assert first_data["sensitivity"]["most_sensitive_parameter"] in {"delay_months", "conversion", "infra_change", "hiring_delay", "mobility"}


def test_scenario_missing_upstream_is_not_presented_as_evaluable():
    result = evaluate_scenarios(DATA, ScenarioInput(), project_result=None, capacity_result=None)
    alternatives = {item["scenario_id"]: item for item in result["scenarios"]}
    assert alternatives["project-reprioritization"]["evaluation_status"] == "insufficient_data"
    assert alternatives["internal-redeployment"]["evaluation_status"] == "insufficient_data"
    assert "Project analysis was not available" in alternatives["project-reprioritization"]["limitations"]


def test_sensitivity_bounds_and_upstream_changes():
    result = sensitivity_analysis(DATA, ScenarioInput())
    delay = next(item for item in result["results"] if item["parameter"] == "delay_months")
    assert delay["bounds"] == {"low": 0.0, "high": 4.0}
    assert delay["outcomes"][0]["capacity_gap"] != delay["outcomes"][1]["capacity_gap"]
    changed = dict(DATA)
    changed["projects"] = [dict(item, weighted=float(item["weighted"]) + 1) for item in DATA["projects"]]
    original = calculate_with_data(DATA, ScenarioInput())
    updated = calculate_with_data(changed, ScenarioInput())
    assert updated["weighted_pipeline"] > original["weighted_pipeline"]


def test_capacity_upstream_is_not_double_adjusted():
    scenario = ScenarioInput(delay_months=2, hiring_delay=1, mobility=2)
    capacity = capacity_analysis(DATA, scenario)
    direct = calculate_with_data(DATA, scenario, capacity_result=capacity)
    expected_gap = calculate_with_data(DATA, scenario)["capacity_gap"]
    assert direct["capacity_gap"] == expected_gap


def test_missing_finance_result_is_insufficient_and_not_ranked():
    result = evaluate_scenarios(DATA, ScenarioInput(), finance_result=None, project_result={"weighted_pipeline": 1.0, "delayed_skills": []}, capacity_result=capacity_analysis(DATA, ScenarioInput()))
    spending = next(item for item in result["scenarios"] if item["scenario_id"] == "spending-reduction")
    assert spending["evaluation_status"] == "insufficient_data"
    assert spending["gross_savings"] is None
    assert "spending-reduction" not in result["ranking"]


def test_ranking_weights_are_normalized_and_explicit():
    result = evaluate_scenarios(DATA, ScenarioInput(), finance_result={"revenue": 10, "opex": 9, "pressure": "high"}, project_result={"weighted_pipeline": 10, "delayed_skills": []}, capacity_result=capacity_analysis(DATA, ScenarioInput()))
    weights = result["ranking_criteria"]
    assert sum(weights.values()) == 1.0
    for item in result["scenarios"]:
        if item["scenario_id"] in result["ranking"]:
            assert abs(item["comparison_score"] - sum(weights[key] * item["ranking_components"][key] for key in weights)) < 0.001


def test_demo_investigation_is_honest():
    response = client.post("/api/investigate")
    assert response.status_code == 200
    data = response.json()
    assert data["meta_call"]["source"] == "Demo fallback"
    assert data["mode"] == "Deterministic demo workflow"


def test_review_persists():
    response = client.post("/api/reviews", json={"recommendation": "needs_evidence", "rationale": "Validate project dates first."})
    assert response.status_code == 200
    assert client.get("/api/reviews").json()[-1]["recommendation"] == "needs_evidence"


def test_data_validation_and_metrics(tmp_path: Path):
    invalid = {"finance": [{"id": "x", "revenue": "bad", "budget": 1, "opex": 1}], "projects": [], "capacity": [], "hiring": []}
    assert validate_data(invalid)["valid"] is False
    assert mae([1, 2], [2, 4]) == 1.5
    assert wape([1, 2], [2, 4]) == 1.0
    assert wape([0], [1]) == 0.0


def test_repository_survives_reopen(tmp_path: Path):
    repository = Repository(tmp_path / "test.sqlite3")
    entry = {"id": "review-1", "timestamp": "2026-10-29T00:00:00+00:00", "reviewer": "Demo planning lead (simulated)", "recommendation": "accepted", "rationale": "Review project dates.", "model": "muse-spark-1.3", "evidence": ["project:P-104"]}
    repository.save_review(entry)
    reopened = Repository(tmp_path / "test.sqlite3")
    assert reopened.reviews()[0]["id"] == "review-1"
    run = {
        "run_id": "run-1",
        "timestamp": "2026-10-29T00:00:00+00:00",
        "mode": "Deterministic demo workflow",
        "model": "muse-spark-1.3",
        "scenario": {"capacity_gap": 8.4},
        "brief": {"evidence": ["project:P-104"]},
        "event": {"type": "project_delay", "budget": 6},
        "steps": [],
    }
    repository.save_investigation(run)
    assert Repository(tmp_path / "test.sqlite3").investigations()[0]["event"]["type"] == "project_delay"


def test_demo_mode_does_not_call_network(monkeypatch):
    async def fail(*args, **kwargs):
        raise AssertionError("network call in demo mode")
    monkeypatch.setattr("httpx.AsyncClient.post", fail)
    client_instance = MetaModelClient()
    assert client_instance.mode == "demo"


def test_local_monitor_baseline_change_suppression_and_persistence(tmp_path: Path):
    source_path = tmp_path / "monitor.json"
    envelope = {
        "source_id": "test-monitor",
        "source_version": "v1",
        "event_type": "project_delay",
        "data": DATA,
    }
    source_path.write_text(json.dumps(envelope), encoding="utf-8")
    repository = Repository(tmp_path / "monitor.sqlite3")
    calls = []

    async def investigate(request, data, quality, snapshot):
        calls.append((request.event_type, snapshot.snapshot_id))
        return {"run_id": f"run-{len(calls)}"}

    import asyncio
    monitor = LocalMonitor(repository, source_path, investigate)
    first = asyncio.run(monitor.check())
    second = asyncio.run(monitor.check())
    assert first["status"] == "baseline"
    assert first["investigation_triggered"] is False
    assert second["status"] == "unchanged"
    assert second["investigation_triggered"] is False
    envelope["data"] = json.loads(json.dumps(DATA))
    envelope["data"]["finance"][-1]["revenue"] = 10.1
    source_path.write_text(json.dumps(envelope), encoding="utf-8")
    changed = asyncio.run(monitor.check())
    assert changed["status"] == "changed_investigated"
    assert changed["investigation_triggered"] is True
    assert changed["run_id"] == "run-1"
    assert len(calls) == 1
    assert Repository(tmp_path / "monitor.sqlite3").monitor_state()["last_run_id"] == "run-1"


def test_local_monitor_rejects_invalid_source_without_investigation(tmp_path: Path):
    source_path = tmp_path / "monitor.txt"
    source_path.write_text("not json", encoding="utf-8")
    repository = Repository(tmp_path / "monitor.sqlite3")
    called = False

    async def investigate(*args):
        nonlocal called
        called = True
        return {"run_id": "unexpected"}

    import asyncio
    result = asyncio.run(LocalMonitor(repository, source_path, investigate).check())
    assert result["status"] == "error"
    assert result["investigation_triggered"] is False
    assert called is False


def test_monitor_snapshot_fixture_is_valid():
    envelope, snapshot, validation = read_monitor_snapshot(Path(__file__).parents[1] / "data" / "monitor_snapshot.example.json")
    assert envelope["event_type"] == "project_delay"
    assert snapshot.snapshot_id.startswith("snapshot:")
    assert validation["valid"] is True


def test_live_meta_validates_structured_output(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"output_text": json.dumps({"changed": "changed", "why_it_matters": "matters", "evidence": ["finance:2026-10"], "uncertainty": "unknown", "options": ["review"], "human_review_next": "check"})}

    class AsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            assert kwargs["json"]["text"]["format"]["type"] == "json_schema"
            return Response()

    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", AsyncClient)
    import asyncio
    result = asyncio.run(MetaModelClient().brief({"scenario": {"weighted_pipeline": 1, "capacity_gap": 1, "infrastructure_spend": 1}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
    assert result["source"] == "Live Meta model"


def test_live_meta_extracts_official_responses_output_shape(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"id": "resp_test", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"changed": "changed", "why_it_matters": "matters", "evidence": ["finance:2026-10"], "uncertainty": "unknown", "options": ["review"], "human_review_next": "check"})}]}], "usage": {"input_tokens": 10, "output_tokens": 12}}

    class AsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return Response()

    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", AsyncClient)
    import asyncio
    result = asyncio.run(MetaModelClient().brief({"scenario": {}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
    assert result["response_id"] == "resp_test"
    assert result["usage"]["total_tokens"] == 22


def test_live_meta_rejects_fabricated_evidence(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"output_text": json.dumps({"changed": "changed", "why_it_matters": "matters", "evidence": ["fabricated:id"], "uncertainty": "unknown", "options": ["review"], "human_review_next": "check"})}

    class AsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return Response()

    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", AsyncClient)
    import asyncio
    try:
        asyncio.run(MetaModelClient().brief({"scenario": {}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
    except RuntimeError as exc:
        assert "unavailable evidence" in str(exc)
    else:
        raise AssertionError("fabricated evidence was accepted")


def test_live_meta_fallback_is_explicit(monkeypatch):
    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    result = MetaModelClient().fallback({"scenario": {"weighted_pipeline": 1, "capacity_gap": 2}, "actions": [], "evidence_ids": ["scenario:baseline"], "investigation_status": "complete"}, "timeout")
    assert result["source"] == "Deterministic fallback (Meta unavailable)"
    assert "timeout" in result["brief"]["uncertainty"]


def test_live_meta_rejects_malformed_output(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"output_text": "{}"}

    class AsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return Response()

    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", AsyncClient)
    import asyncio
    try:
        asyncio.run(MetaModelClient().brief({"scenario": {}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
    except RuntimeError as exc:
        assert "failed safely" in str(exc)
    else:
        raise AssertionError("malformed output was accepted")


def test_live_meta_missing_credentials_is_clear(monkeypatch):
    monkeypatch.setenv("META_MODEL_MODE", "live")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    import asyncio
    try:
        asyncio.run(MetaModelClient().brief({"scenario": {}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
    except RuntimeError as exc:
        assert "MODEL_API_KEY" in str(exc)
    else:
        raise AssertionError("missing credentials were accepted")


def test_live_meta_http_failures_are_safe(monkeypatch):
    import asyncio

    class Response:
        def __init__(self, status): self.status_code = status
        def raise_for_status(self): raise RuntimeError(f"server {self.status_code}")
        def json(self): return {}

    class AsyncClient:
        def __init__(self, response): self.response = response
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return self.response

    for status, expected in ((401, "authentication"), (429, "rate limit"), (500, "failed safely")):
        monkeypatch.setenv("META_MODEL_MODE", "live")
        monkeypatch.setenv("MODEL_API_KEY", "test-key")
        monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: AsyncClient(Response(status)))
        try:
            asyncio.run(MetaModelClient().brief({"scenario": {}, "actions": [], "evidence_ids": ["finance:2026-10"]}))
        except RuntimeError as exc:
            assert expected in str(exc).lower()
        else:
            raise AssertionError(f"HTTP {status} was accepted")


def test_action_schema_and_hiring_control_contract():
    response = client.post("/api/scenarios", json={"delay_months": 1, "conversion": .82, "infra_change": .12, "hiring_delay": 2, "mobility": 0})
    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert {"time_to_effect", "uncertainty", "approval", "cost_unit"} <= action.keys()
    assert "undefined" not in (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "hiring_delay" in (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")


def test_invalid_source_data_blocks_analysis(monkeypatch):
    monkeypatch.setitem(DATA["finance"][0], "revenue", "invalid")
    assert client.post("/api/investigate").status_code == 503
    monkeypatch.setitem(DATA["finance"][0], "revenue", 12.4)


def test_event_types_select_different_investigation_paths():
    project = run_investigation(DATA, ScenarioInput(), "project_delay", 4)
    infrastructure = run_investigation(DATA, ScenarioInput(), "infrastructure_cost", 4)
    assert project[0].agent == "Project demand analyst"
    assert infrastructure[0].agent == "Finance analyst"
    assert [step.agent for step in project] != [step.agent for step in infrastructure]


def test_downstream_steps_record_real_upstream_handoff():
    steps = run_investigation(DATA, ScenarioInput(), "project_delay", 4)
    capacity = next(step for step in steps if step.agent == "Workforce capacity analyst")
    assert capacity.inputs == ["Project demand analyst"]
    assert capacity.result["upstream_project_analysis"]["flagged_projects"] == 2


def test_tool_arguments_and_budget_are_bounded():
    try:
        validate_tool_request("arbitrary_code", {}, {"finance_analysis"})
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("unsupported tool was accepted")
    assert len(run_investigation(DATA, ScenarioInput(), "project_delay", 2)) == 2
    tool, arguments = validate_model_tool_request(
        {"type": "tool_request", "tool": "finance_analysis", "arguments": {}},
        {"finance_analysis"},
    )
    assert tool == "finance_analysis"
    assert arguments == {}


def test_evaluation_has_explicit_fixture_ground_truth():
    result = client.get("/api/evaluation").json()["policy"]
    assert result["status"] == "synthetic policy evaluation"
    assert all(item["ground_truth"] is True for item in result["fixtures"])


def test_evidence_review_gate_for_budgets_one_four_and_six():
    cases = (
        ("project_delay", 1, "incomplete"),
        ("project_delay", 4, "incomplete"),
        ("project_delay", 6, "complete"),
        ("infrastructure_cost", 1, "incomplete"),
        ("infrastructure_cost", 4, "incomplete"),
        ("infrastructure_cost", 6, "complete"),
    )
    for event_type, budget, expected_status in cases:
        response = client.post("/api/investigate", json={"event_type": event_type, "budget": budget})
        assert response.status_code == 200
        data = response.json()
        assert data["investigation_status"] == expected_status
        assert data["event"]["budget"] == budget
        assert data["review"]["completed"] is (expected_status == "complete")
        if expected_status == "incomplete":
            assert data["review"]["mandatory_missing"] == ["Evidence and policy reviewer"]
        assert set(data["brief"]["evidence"]).issubset(
            {item["id"] for group in ("finance", "projects", "hiring") for item in DATA[group]}
            | {f"capacity:{item['skill']}" for item in DATA["capacity"]}
            | {"investment:ai-2026-10", "scenario:baseline"}
        )


def test_action_planner_receives_all_available_upstream_results():
    project_steps = run_investigation(DATA, ScenarioInput(), "project_delay", 4)
    project_planner = next(step for step in project_steps if step.agent == "Preventive action planner")
    assert {"Workforce capacity analyst", "Scenario analyst"} <= set(project_planner.inputs)
    assert {"Workforce capacity analyst", "Scenario analyst"} <= set(project_planner.result["upstream_results"])

    infrastructure_steps = run_investigation(DATA, ScenarioInput(), "infrastructure_cost", 4)
    infrastructure_planner = next(step for step in infrastructure_steps if step.agent == "Preventive action planner")
    assert "Scenario analyst" in infrastructure_planner.inputs
    assert "Scenario analyst" in infrastructure_planner.result["upstream_results"]
    assert "Workforce capacity analyst" not in infrastructure_planner.result["upstream_results"]


def test_failed_upstream_result_is_disclosed_and_degrades(monkeypatch):
    def fail_project_analysis(data):
        raise ValueError("project evidence unavailable")

    monkeypatch.setattr("app.agents.project_analysis", fail_project_analysis)
    steps = run_investigation(DATA, ScenarioInput(), "project_delay", 5)
    project = next(step for step in steps if step.agent == "Project demand analyst")
    planner = next(step for step in steps if step.agent == "Preventive action planner")
    assert project.status == "failed"
    assert planner.status == "completed"
    assert any("Project demand analyst" in item for item in planner.result["limitations"])


def test_evidence_review_is_last_in_each_policy():
    for event_type in ("project_delay", "infrastructure_cost"):
        selections = DeterministicPlanner().select(InvestigationContext(event_type, 6))
        assert selections[-1].tool == "evidence_review"
        assert "evidence_review" not in [selection.tool for selection in selections[:-1]]


def test_meta_planner_rejects_invalid_dependencies_budget_and_unsafe_arguments():
    planner = MetaModelPlanner({"capacity_analysis", "finance_analysis"})
    context = InvestigationContext("project_delay", 2)
    for response, expected in (
        ({"type": "tool_request", "tool": "shell", "arguments": {}}, "Unsupported"),
        ({"type": "tool_request", "tool": "capacity_analysis", "arguments": {}}, "dependencies"),
    ):
        try:
            planner.select_request(response, context)
        except ValueError as exc:
            assert expected.lower() in str(exc).lower()
        else:
            raise AssertionError("invalid planner request was accepted")
    try:
        planner.select_request(
            {"type": "tool_request", "tool": "finance_analysis", "arguments": {"x": "shell:dir"}},
            InvestigationContext("project_delay", 1, ("finance_analysis",)),
        )
    except ValueError as exc:
        assert "duplicate" in str(exc).lower() or "budget" in str(exc).lower()
    else:
        raise AssertionError("unsafe or duplicate planner request was accepted")


def test_synthetic_source_snapshot_is_versioned_and_reproducible():
    validation = validate_data(DATA)
    first = SyntheticSourceAdapter(DATA, validation).snapshot()
    second = SyntheticSourceAdapter(DATA, validation).snapshot()
    assert first.snapshot_id == second.snapshot_id
    assert first.source_version == "synthetic-fixture-v1"
    assert first.source_timestamp is None
    assert first.ingested_at


def test_event_replay_and_history_expose_source_and_policy():
    replay = client.post(
        "/api/events/replay",
        json={"event_id": "evt-demo-1", "event_type": "infrastructure_cost", "budget": 6},
    )
    assert replay.status_code == 200
    data = replay.json()
    assert data["event"]["event_id"] == "evt-demo-1"
    assert data["source"]["snapshot_id"].startswith("snapshot:")
    assert data["policy"]["name"] == "deterministic-policy-v1"
    replayed = client.post(
        "/api/events/replay",
        json={
            "event_id": "evt-demo-1-replay",
            "event_type": "infrastructure_cost",
            "budget": 6,
            "snapshot_id": data["source"]["snapshot_id"],
        },
    )
    replayed_data = replayed.json()
    assert replayed_data["run_id"] != data["run_id"]
    assert replayed_data["source"]["snapshot_id"] == data["source"]["snapshot_id"]
    assert replayed_data["scenario"] == data["scenario"]
    assert [step["result"] for step in replayed_data["steps"]] == [step["result"] for step in data["steps"]]
    history = client.get("/api/history")
    assert history.status_code == 200
    assert any(item["id"] == data["run_id"] and item["source"]["snapshot_id"] == data["source"]["snapshot_id"] for item in history.json())


def test_json_and_csv_ingestion_provenance_and_stable_snapshot(tmp_path: Path):
    json_path = tmp_path / "finance.json"
    json_path.write_text('[{"id":"F-1","revenue":10,"event_timestamp":"2026-10-01T00:00:00Z"}]', encoding="utf-8")
    json_adapter = FileSourceAdapter(json_path, "finance", "finance-v1", ("id", "revenue"))
    first = json_adapter.ingest()
    second = json_adapter.ingest()
    assert first.snapshot_id == second.snapshot_id
    assert first.records[0].evidence_id.startswith("finance:")
    assert first.records[0].event_timestamp.endswith("Z")
    assert first.records[0].provenance == "finance.json#record-1"
    assert first.ingested_at != "" and first.records[0].ingested_at != ""

    csv_path = tmp_path / "capacity.csv"
    csv_path.write_text("skill,capacity,demand\nCloud,38,45\n", encoding="utf-8")
    csv_result = FileSourceAdapter(csv_path, "capacity", "capacity-v1", ("skill", "capacity", "demand")).ingest()
    assert len(csv_result.records) == 1
    assert "source event timestamp is unavailable" in csv_result.warnings


def test_invalid_source_record_is_rejected_with_reason(tmp_path: Path):
    path = tmp_path / "projects.json"
    path.write_text('[{"id":"P-1","status":"delayed"}]', encoding="utf-8")
    result = FileSourceAdapter(path, "projects", "projects-v1", ("id", "status", "weighted")).ingest()
    assert not result.records
    assert result.rejected[0].error == "Missing required fields: weighted"
    assert result.rejected[0].provenance.endswith("#record-1")


def test_scenario_and_actions_consume_upstream_results():
    scenario = ScenarioInput()
    finance = {"revenue": 5.0, "pressure": "high"}
    projects = {"weighted_pipeline": 1.0, "delayed_skills": ["Cloud"]}
    capacity = {"gap_by_skill": [{"skill": "Cloud", "gap": 0.0, "capacity": 45.0, "demand": 45.0}]}
    result = calculate_with_data(DATA, scenario, finance_result=finance, project_result=projects, capacity_result=capacity)
    assert result["inputs_consumed"] == ["finance_analysis", "project_analysis", "capacity_analysis"]
    assert result["weighted_pipeline"] == 0.82
    actions = action_plan(DATA, scenario, scenario_result=result, finance_result=finance, project_result=projects, capacity_result=capacity)
    mobility = next(item for item in actions if item["id"] == "mobility")
    assert mobility["eligible"] is False
    assert mobility["inputs_consumed"] == ["scenario_result", "capacity_analysis"]


def test_replay_same_snapshot_is_deterministic_except_run_and_ingestion_metadata(tmp_path: Path):
    repository = Repository(tmp_path / "replay.sqlite3")
    snapshot = SyntheticSourceAdapter(DATA, validate_data(DATA)).snapshot()
    repository.save_snapshot({
        "snapshot_id": snapshot.snapshot_id,
        "source_id": snapshot.source_name,
        "source_version": snapshot.source_version,
        "ingested_at": snapshot.ingested_at,
        "source_timestamp": snapshot.source_timestamp,
        "provenance": snapshot.provenance,
        "validation": snapshot.validation,
        "data": snapshot.data,
    })
    restored = repository.snapshot(snapshot.snapshot_id)
    assert restored["data"] == DATA
    assert restored["source_version"] == "synthetic-fixture-v1"


def test_outcome_validation_persists_across_repository_reopen(tmp_path: Path):
    repository = Repository(tmp_path / "outcomes.sqlite3")
    repository.save_investigation({
        "run_id": "run-outcome",
        "timestamp": "2026-10-29T00:00:00+00:00",
        "mode": "Deterministic demo workflow",
        "model": "muse-spark-1.3",
        "scenario": {},
        "brief": {"evidence": ["project:P-104"]},
        "event": {"type": "project_delay"},
        "steps": [],
    })
    entry = {
        "id": "outcome-1", "investigation_id": "run-outcome", "category": "capacity",
        "value": 2.0, "unit": "units", "observed_on": "2026-11-01",
        "evidence_source": "human supplied operations report",
        "provenance": "explicitly_supplied", "created_at": "2026-11-02T00:00:00+00:00",
    }
    repository.save_outcome(entry)
    assert Repository(tmp_path / "outcomes.sqlite3").outcomes("run-outcome")[0]["provenance"] == "explicitly_supplied"


def test_outcome_api_validates_run_and_frontend_transparency_contract():
    response = client.post("/api/outcomes", json={
        "investigation_id": "missing-run", "category": "capacity",
        "observed_on": "2026-11-01", "evidence_source": "operator note",
    })
    assert response.status_code == 404
    frontend = (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "snapshot_id" in frontend
    assert "investigation_status" in frontend
    assert "/api/history" in frontend
    assert "/api/outcomes" in frontend


def test_outcome_projection_comparison_is_descriptive():
    run = client.post("/api/investigate", json={"event_type": "project_delay", "budget": 6}).json()
    saved = client.post("/api/outcomes", json={
        "investigation_id": run["run_id"], "category": "capacity", "value": 4,
        "unit": "units", "observed_on": "2026-11-01", "evidence_source": "human operations note",
    })
    assert saved.status_code == 200
    comparison = client.get(f"/api/outcomes/compare/{run['run_id']}")
    assert comparison.status_code == 200
    item = comparison.json()[-1]
    assert item["status"] == "comparable"
    assert item["difference"] is not None
    assert "causal" in item["explanation"]


def test_temporal_evaluation_excludes_leakage_and_reports_small_samples():
    investigations = [
        {
            "id": "run-eval-1",
            "timestamp": "2026-10-01T00:00:00+00:00",
            "scenario": {"capacity_gap": 4.0},
            "source": {"snapshot_id": "snapshot:one"},
            "policy": {"name": "deterministic-policy-v1"},
        },
        {
            "id": "run-eval-2",
            "timestamp": "2026-10-05T00:00:00+00:00",
            "scenario": {"capacity_gap": 3.0},
            "source": {"snapshot_id": "snapshot:two"},
            "policy": {"name": "deterministic-policy-v1"},
        },
    ]
    outcomes = [
        {"id": "out-1", "investigation_id": "run-eval-1", "category": "capacity", "value": 5.0, "unit": "units", "observed_on": "2026-10-10", "created_at": "2026-10-11"},
        {"id": "out-2", "investigation_id": "run-eval-2", "category": "capacity", "value": 2.0, "unit": "units", "observed_on": "2026-10-12", "created_at": "2026-10-13"},
        {"id": "out-leak", "investigation_id": "run-eval-2", "category": "capacity", "value": 2.0, "unit": "units", "observed_on": "2026-10-04", "created_at": "2026-10-04"},
    ]
    result = evaluate_history(investigations, outcomes, category="capacity", minimum_samples=2)
    assert result["status"] == "evaluated"
    assert result["sample_count"] == 2
    assert result["metrics"]["baseline"]["sample_count"] == 1
    assert any(item["reason"] == "prediction_after_observation" for item in result["excluded"])


def test_temporal_evaluation_api_persists_insufficient_result():
    response = client.post("/api/evaluations", json={"category": "capacity", "minimum_samples": 999})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_samples"
    assert client.get("/api/evaluations").status_code == 200


def test_local_auth_roles_tenant_boundary_and_audit(monkeypatch):
    monkeypatch.setenv("WRI_AUTH_ENABLED", "true")
    assert client.get("/api/overview").status_code == 401
    login = client.post("/api/auth/login", json={"username": "reviewer", "password": "reviewer-demo"})
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}", "X-WRI-Tenant": "demo-tenant"}
    assert client.get("/api/overview", headers=headers).status_code == 200
    assert client.post("/api/reviews", headers=headers, json={"recommendation": "accepted", "rationale": "Review evidence."}).status_code == 403
    assert client.get("/api/overview", headers={**headers, "X-WRI-Tenant": "other-tenant"}).status_code == 403
    operator = client.post("/api/auth/login", json={"username": "operator", "password": "operator-demo"}).json()["token"]
    operator_headers = {"Authorization": f"Bearer {operator}", "X-WRI-Tenant": "demo-tenant"}
    assert client.post("/api/reviews", headers=operator_headers, json={"recommendation": "accepted", "rationale": "Review evidence."}).status_code == 200
    assert any(item["action"] == "review_created" for item in client.get("/api/audit", headers=operator_headers).json())
    monkeypatch.setenv("WRI_AUTH_ENABLED", "false")


def test_event_delivery_is_idempotent_and_work_timeline_is_persisted(tmp_path: Path):
    repository = Repository(tmp_path / "work.sqlite3")
    first = repository.create_work_item({
        "id": "work-1",
        "event_id": "event-1",
        "payload": {"event_type": "project_delay"},
        "created_at": "2026-11-01T00:00:00+00:00",
        "updated_at": "2026-11-01T00:00:00+00:00",
    })
    second = repository.create_work_item({
        "id": "work-duplicate",
        "event_id": "event-1",
        "payload": {"event_type": "project_delay"},
        "created_at": "2026-11-01T00:01:00+00:00",
        "updated_at": "2026-11-01T00:01:00+00:00",
    })
    assert first["id"] == second["id"] == "work-1"
    repository.update_work_item("work-1", "running", "2026-11-01T00:02:00+00:00", increment_attempt=True)
    recovered = Repository(tmp_path / "work.sqlite3").recover_work_items("2026-11-01T00:03:00+00:00")
    assert recovered == 1
    timeline = Repository(tmp_path / "work.sqlite3").work_timeline("work-1")
    assert [item["status"] for item in timeline] == ["queued", "running", "queued"]
    assert Repository(tmp_path / "work.sqlite3").work_item("work-1")["error"] == "Recovered after process restart."


def test_agent_runtime_catalog_trace_and_tool_contracts():
    catalog = client.get("/api/agents")
    tools = client.get("/api/tools")
    assert catalog.status_code == tools.status_code == 200
    names = {item["name"] for item in catalog.json()["agents"]}
    assert catalog.json()["supervisor"]["name"] == "EnterpriseIntelligenceSupervisor"
    assert "Financial Intelligence Agent" in names
    assert any(item["name"] == "finance_analysis" and item["read_only"] for item in tools.json())
    run = client.post("/api/investigate", json={"event_type": "project_delay", "budget": 6}).json()
    trace = client.get(f"/api/investigations/{run['run_id']}/trace")
    assert trace.status_code == 200
    assert trace.json()["trace"]
    assert all(item["selected_tools"] for item in trace.json()["trace"])


def test_scripted_live_supervisor_plans_and_agents_use_provider_without_network():
    provider = ScriptedModelProvider([
        {"tools": ["project_analysis", "finance_analysis", "evidence_review"]},
        {"status": "completed", "finding": "Projects reviewed", "evidence": ["project:P-104"]},
        {"status": "completed", "finding": "Finance reviewed", "evidence": ["finance:2026-10"]},
        {"status": "completed", "finding": "Evidence reviewed", "evidence": ["project:P-104"]},
    ])
    runtime = __import__("app.agent_runtime", fromlist=["build_agent_runtime"]).build_agent_runtime("live", provider=provider)
    supervisor = EnterpriseIntelligenceSupervisor(runtime)
    context = __import__("app.orchestration", fromlist=["InvestigationContext"]).InvestigationContext("project_delay", 3)
    plan = supervisor.plan(context)
    assert [item.tool for item in plan] == ["project_analysis", "finance_analysis", "evidence_review"]
    calls = []
    supervisor.execute(context, lambda selection: calls.append(selection.tool) or type("Result", (), {"status": "completed", "evidence": []})())
    assert calls == ["project_analysis", "finance_analysis", "evidence_review"]
    assert len(provider.calls) == 4
    assert all(item.selected_tools for item in runtime.traces)


def test_tool_registry_invocation_enforces_permissions_and_callable_contract():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("safe_tool", "test", {"type": "object"}, {"type": "object"}),
        lambda arguments: {"value": arguments["value"]},
    )
    assert registry.invoke("safe_tool", {"value": 3}, permissions=("read:investigation",))["value"] == 3
    with pytest.raises(PermissionError):
        registry.invoke("safe_tool", {"value": 3}, permissions=())


def test_live_supervisor_supports_agent_handoff_and_observation_replanning():
    provider = ScriptedModelProvider([
        {"tools": ["project_analysis", "evidence_review"]},
        {"status": "completed", "finding": "Project delay needs finance review", "evidence": ["project:P-104"], "handoff_to": ["Financial Intelligence Agent"]},
        {"additional_tools": []},
        {"status": "completed", "finding": "Financial analysis completed", "evidence": ["finance:2026-10"]},
        {"status": "completed", "finding": "Evidence review completed", "evidence": ["project:P-104"]},
    ])
    runtime = __import__("app.agent_runtime", fromlist=["build_agent_runtime"]).build_agent_runtime("live", provider=provider)
    supervisor = EnterpriseIntelligenceSupervisor(runtime)
    context = __import__("app.orchestration", fromlist=["InvestigationContext"]).InvestigationContext("project_delay", 3)
    calls = []
    supervisor.execute(
        context,
        lambda selection: calls.append(selection.tool) or type(
            "Result", (), {"status": "completed", "evidence": ["project:P-104"]}
        )(),
    )
    assert calls == ["project_analysis", "finance_analysis", "evidence_review"]
    assert any(event["event"] == "supervisor_replan" for event in runtime.model_events)
    assert runtime.traces[0].model_invoked is True
    assert runtime.traces[0].handoff_to == ["Financial Intelligence Agent"]


def test_full_investigation_entrypoint_uses_model_driven_supervisor_and_registered_tools(monkeypatch):
    from app import agents as agent_module
    from app.agent_runtime import build_agent_runtime

    model_responses = [{
        "tasks": [
            {"tool": "project_analysis", "reason": "Inspect delayed demand", "dependencies": []},
            {"tool": "finance_analysis", "reason": "Check financial exposure", "dependencies": []},
            {"tool": "capacity_analysis", "reason": "Check aggregate skills gap", "dependencies": ["project_analysis"]},
            {"tool": "scenario_analysis", "reason": "Compare outcomes", "dependencies": ["project_analysis", "finance_analysis", "capacity_analysis"]},
            {"tool": "action_plan", "reason": "Evaluate preventive options", "dependencies": ["scenario_analysis"]},
            {"tool": "evidence_review", "reason": "Independently review evidence", "dependencies": []},
        ]
    }]
    model_responses.extend([
        {"status": "completed", "finding": f"{role} analysis complete", "evidence": []}
        for role in ["project", "finance", "capacity", "scenario", "alternatives", "review"]
    ])
    provider = ScriptedModelProvider(model_responses)
    runtime = build_agent_runtime("live", provider=provider)
    monkeypatch.setattr(agent_module, "build_agent_runtime", lambda mode: runtime)
    trace = []
    results = run_investigation(DATA, ScenarioInput(), "project_delay", 6, trace_sink=trace)
    assert [result.status for result in results] == ["completed"] * 6
    assert len(provider.calls) == 7
    assert {item["agent"] for item in trace} >= {
        "Project and Business Demand Agent",
        "Financial Intelligence Agent",
        "Workforce Capacity and Skills Agent",
        "Scenario and Forecasting Agent",
        "Preventive Alternatives Agent",
        "Evidence, Risk and Policy Review Agent",
    }
    assert all(item["model_invoked"] for item in trace)
