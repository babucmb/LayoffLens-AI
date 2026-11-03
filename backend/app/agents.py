from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import os
from typing import Any
import httpx
from urllib.parse import urlparse

from .analytics import action_plan, calculate_scenario, capacity_analysis, finance_analysis, project_analysis
from .analytics_engine import (
    anomalies,
    demand_intelligence,
    forecast_suite,
    operations_intelligence,
    financial_intelligence,
    workforce_intelligence,
)
from .agent_runtime import EnterpriseIntelligenceSupervisor, build_agent_runtime



from .orchestration import EVENT_POLICIES, DeterministicPlanner, InvestigationContext, MetaModelPlanner, validate_model_tool_request
from .schemas import AgentResult, ScenarioInput


def run_agent(
    name: str,
    evidence: list[str],
    operation: Callable[[], dict[str, Any]],
    *,
    reason: str,
    inputs: list[str] | None = None,
) -> AgentResult:
    try:
        return AgentResult(
            agent=name,
            status="completed",
            evidence=evidence,
            result=operation(),
            reason=reason,
            inputs=inputs or [],
        )
    except (KeyError, TypeError, ValueError) as exc:
        return AgentResult(
            agent=name,
            status="failed",
            evidence=evidence,
            error=f"{type(exc).__name__}: {exc}",
            reason=reason,
            inputs=inputs or [],
        )


def _evidence_ids(data: dict[str, Any]) -> set[str]:
    return {
        *[item["id"] for group in ("finance", "projects", "hiring") for item in data[group]],
        *[f"capacity:{item['skill']}" for item in data["capacity"]],
        "investment:ai-2026-10",
        "scenario:baseline",
    }


def validate_tool_request(tool: str, arguments: dict[str, Any], allowed: set[str]) -> None:
    if tool not in allowed:
        raise ValueError(f"Unsupported investigation tool: {tool}")
    if tool == "capacity_analysis" and not isinstance(arguments.get("scenario"), ScenarioInput):
        raise ValueError("capacity_analysis requires a ScenarioInput")


def run_investigation(
    data: dict[str, Any],
    scenario: ScenarioInput,
    event_type: str = "project_delay",
    budget: int = 6,
    trace_sink: list[dict[str, Any]] | None = None,
) -> list[AgentResult]:
    context = InvestigationContext(event_type=event_type, budget=budget)
    runtime = build_agent_runtime(os.getenv("WRI_AGENT_MODE", "simulation").lower())
    supervisor = EnterpriseIntelligenceSupervisor(runtime)
    selections = supervisor.plan(context)
    results: dict[str, AgentResult] = {}
    tool_to_agent = {
        "business_signal": "Business Signal Intelligence Agent",
        "external_research": "External Research and Market Intelligence Agent",
        "finance_analysis": "Finance analyst",
        "project_analysis": "Project demand analyst",
        "capacity_analysis": "Workforce capacity analyst",
        "infrastructure_analysis": "Infrastructure and Operational Intelligence Agent",
        "scenario_analysis": "Scenario analyst",
        "action_plan": "Preventive action planner",
        "evidence_review": "Evidence and policy reviewer",
        "executive_report": "Executive Intelligence and Reporting Agent",
        "sales_demand_analysis": "Sales and Demand Intelligence Agent",
        "ai_transformation_analysis": "AI Transformation Intelligence Agent",
        "forecast_risk_analysis": "Forecast and Risk Intelligence Agent",
        "infrastructure_operations_analysis": "Infrastructure and Operations Intelligence Agent",
    }

    def execute(name: str, evidence: list[str], operation: Callable[[], dict[str, Any]], reason: str, inputs: list[str] = ()) -> AgentResult:
        results[name] = run_agent(name, evidence, operation, reason=reason, inputs=list(inputs))
        return results[name]

    def execute_selection(selection: Any) -> AgentResult:
        name = tool_to_agent[selection.tool]
        if selection.tool == "business_signal":
            return execute(
                name,
                ["scenario:baseline"],
                lambda: {
                    "event_type": event_type,
                    "trigger": "Investigation event supplied by the application.",
                    "classification": "business_signal_requires_investigation",
                    "verified_inputs": ["event_type", "validated source snapshot"],
                    "hypotheses": ["Underlying cause requires specialist evidence; event type alone is not causal proof."],
                },
                selection.reason,
            )
        elif selection.tool == "external_research":
            def retrieve_public_research() -> dict[str, Any]:
                api_key = os.getenv("TAVILY_API_KEY", "")
                if not api_key:
                    return {
                        "provider": "tavily",
                        "status": "not_configured",
                        "results": [],
                        "limitations": ["TAVILY_API_KEY is not configured; no live public research was retrieved."],
                    }
                query = f"{data.get('company', 'organization')} {event_type.replace('_', ' ')} business financial industry developments"
                try:
                    response = httpx.post(
                        os.getenv("TAVILY_API_URL", "https://api.tavily.com/search"),
                        json={"api_key": api_key, "query": query, "search_depth": "basic", "max_results": 5, "include_answer": False},
                        timeout=float(os.getenv("WRI_RESEARCH_TIMEOUT_SECONDS", "15")),
                    )
                    if response.status_code in {401, 403}:
                        return {"provider": "tavily", "status": "authentication_failed", "query": query, "results": [], "limitations": ["Tavily authentication failed; enterprise evidence remains authoritative."]}
                    if response.status_code == 429:
                        return {"provider": "tavily", "status": "rate_limited", "query": query, "results": [], "limitations": ["Tavily rate limit reached; no external context was used."]}
                    response.raise_for_status()
                    body = response.json()
                except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
                    return {"provider": "tavily", "status": "provider_failure", "query": query, "results": [], "limitations": [f"External research unavailable: {type(exc).__name__}."]}
                results = []
                for item in body.get("results", []):
                    if not isinstance(item, dict) or not isinstance(item.get("url"), str) or urlparse(item["url"]).scheme not in {"http", "https"}:
                        continue
                    results.append({
                        "title": str(item.get("title", "")),
                        "url": str(item["url"]),
                        "excerpt": str(item.get("content", ""))[:4000],
                        "published_at": item.get("published_date"),
                        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "provider": "tavily",
                        "source_type": "external_research",
                        "verification_status": "retrieved_context_not_enterprise_proof",
                    })
                return {"provider": "tavily", "status": "retrieved" if results else "empty", "query": query, "results": results, "limitations": ["Retrieved public context is untrusted and cannot alter deterministic calculations."]}
            return execute(name, [], retrieve_public_research, selection.reason)
        elif selection.tool == "infrastructure_analysis":
            return execute(
                name,
                ["investment:ai-2026-10", *[f"capacity:{row['skill']}" for row in data["capacity"]]],
                lambda: {
                    "infrastructure_spend": round(float(data.get("investment", {}).get("ai_spend", 0)) + float(data.get("investment", {}).get("gpu_spend", 0)), 3),
                    "adoption_signal": data.get("investment", {}).get("adoption"),
                    "quality_signal": data.get("investment", {}).get("quality"),
                    "capacity_by_skill": [
                        {"skill": row["skill"], "capacity": row["capacity"], "demand": row["demand"], "gap": round(float(row["demand"]) - float(row["capacity"]), 3)}
                        for row in data["capacity"]
                    ],
                    "limitations": ["Infrastructure provider telemetry is not connected; values come from the validated supplied snapshot."],
                },
                selection.reason,
            )
        elif selection.tool == "sales_demand_analysis":
            return execute(
                name,
                [row.get("record_id", row.get("id", "")) for row in data.get("sales", [])],
                lambda: demand_intelligence(data) if "sales" in data else {"status": "insufficient_data", "limitations": ["Canonical sales data is unavailable in this investigation snapshot."]},
                selection.reason,
            )
        elif selection.tool == "ai_transformation_analysis":
            result = operations_intelligence(data)["ai_transformation"] if "ai_transformation" in data else {"status": "insufficient_data", "limitations": ["Canonical AI transformation data is unavailable in this investigation snapshot."]}
            return execute(
                name,
                result.get("evidence", []),
                lambda result=result: result,
                selection.reason,
            )
        elif selection.tool == "forecast_risk_analysis":
            return execute(
                name,
                [row.get("record_id", row.get("id", "")) for row in data.get("finance", [])],
                lambda: {"forecasts": forecast_suite(data, 90), "anomalies": anomalies(data, 1.0), "uncertainty": "Forecast bounds are not statistical confidence intervals."} if "organization" in data else {"status": "insufficient_data", "limitations": ["Phase 2 canonical forecast inputs are unavailable in this investigation snapshot."]},
                selection.reason,
            )
        elif selection.tool == "infrastructure_operations_analysis":
            result = operations_intelligence(data) if "cloud" in data else {"status": "insufficient_data", "limitations": ["Canonical infrastructure data is unavailable in this investigation snapshot."]}
            evidence = result.get("cloud", {}).get("evidence", []) + result.get("facilities", {}).get("evidence", [])
            return execute(
                name,
                evidence,
                lambda result=result: result,
                selection.reason,
            )
        elif selection.tool == "executive_report":
            def build_executive_report() -> dict[str, Any]:
                findings = [
                    {"agent": item.agent, "status": item.status, "evidence": item.evidence, "result": item.result or {}}
                    for item in results.values()
                ]
                return {
                    "title": "LayoffLens AI workforce resilience investigation",
                    "event_type": event_type,
                    "findings": findings,
                    "human_review_required": True,
                    "decision_boundary": "Decision support only; no employee-level termination recommendation or automated employment action.",
                }
            return execute(name, sorted({e for item in results.values() for e in item.evidence}), build_executive_report, selection.reason, [item.agent for item in results.values()])
        elif selection.tool == "project_analysis":
            validate_tool_request(selection.tool, {}, {"project_analysis", "finance_analysis", "capacity_analysis", "scenario_analysis", "action_plan"})
            return execute(name, [p["id"] for p in data["projects"]], lambda: project_analysis(data), selection.reason)
        elif selection.tool == "finance_analysis":
            validate_tool_request(selection.tool, {}, {"project_analysis", "finance_analysis", "capacity_analysis", "scenario_analysis", "action_plan"})
            return execute(name, [data["finance"][-1]["id"]], lambda: finance_analysis(data), selection.reason)
        elif selection.tool == "capacity_analysis":
            upstream = results.get("Project demand analyst")
            return execute(
                name,
                [f"capacity:{r['skill']}" for r in data["capacity"]],
                lambda upstream=upstream: {
                    **capacity_analysis(data, scenario),
                    "upstream_project_analysis": upstream.result if upstream and upstream.status == "completed" else {},
                },
                selection.reason,
                ["Project demand analyst"] if upstream else [],
            )
        elif selection.tool == "scenario_analysis":
            inputs = [step for step in ("Project demand analyst", "Finance analyst", "Workforce capacity analyst") if step in results]
            return execute(
                name,
                ["scenario:baseline"],
                lambda: calculate_scenario(
                    data,
                    scenario,
                    finance_result=results.get("Finance analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                    project_result=results.get("Project demand analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                    capacity_result=results.get("Workforce capacity analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                ),
                selection.reason,
                inputs,
            )
        elif selection.tool == "action_plan":
            upstream_results = {
                step.agent: step.result
                for step in results.values()
                if step.agent in {"Finance analyst", "Project demand analyst", "Workforce capacity analyst", "Scenario analyst"}
                and step.status == "completed"
            }
            missing = [required for required in ("Scenario analyst",) if required not in upstream_results]
            failed_upstream = [
                step.agent for step in results.values()
                if step.agent in {"Finance analyst", "Project demand analyst", "Workforce capacity analyst", "Scenario analyst"}
                and step.status == "failed"
            ]

            def plan_actions() -> dict[str, Any]:
                if missing:
                    raise ValueError(f"Required upstream result unavailable: {', '.join(missing)}")
                return {
                    "actions": action_plan(
                        data,
                        scenario,
                        scenario_result=results["Scenario analyst"].result,
                        finance_result=results.get("Finance analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                        project_result=results.get("Project demand analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                        capacity_result=results.get("Workforce capacity analyst", AgentResult(agent="", status="failed", evidence=[])).result or None,
                    ),
                    "upstream_results": upstream_results,
                    "limitations": [f"Upstream step failed: {agent}" for agent in failed_upstream],
                }

            return execute(name, ["capacity:Cloud", "capacity:Data", "investment:ai-2026-10"], plan_actions, selection.reason, list(upstream_results))
        elif selection.tool == "evidence_review":
            completed = [result for result in results.values() if result.status == "completed"]
            cited = sorted({item for result in completed for item in result.evidence})
            unsupported = sorted(set(cited) - _evidence_ids(data))
            return execute(
                name,
                cited,
                lambda unsupported=unsupported: {
                    "aggregate_only": True,
                    "unsupported_claims": unsupported,
                    "review": "Evidence references are present for completed steps." if not unsupported else "Unsupported evidence references require human review.",
                },
                selection.reason,
                [result.agent for result in completed],
            )
        raise ValueError(f"Unsupported planned tool: {selection.tool}")

    # Bind investigation-scoped implementations into the generic tool registry.
    # The registry now performs permission, argument-schema, callable, and result checks.
    for tool_name in tool_to_agent:
        runtime_handler = lambda arguments, tool_name=tool_name: {
            "agent_result": execute_selection(
                type("Selection", (), {
                    "tool": tool_name,
                    "reason": "Invoked through the validated registered-tool executor.",
                    "required_dependencies": tuple(),
                })()
            ).model_dump()
        }
        runtime.registry.bind(tool_name, runtime_handler)

    def invoke_registered_tool(selection: Any) -> AgentResult:
        payload = runtime.registry.invoke(
            selection.tool, {}, permissions=("read:investigation", "read:aggregate")
        )
        return AgentResult.model_validate(payload["agent_result"])

    supervisor.execute(context, invoke_registered_tool)
    if trace_sink is not None:
        trace_sink.extend(
            {
                "agent": trace.agent,
                "status": trace.status,
                "reason": trace.reason,
                "selected_tools": trace.selected_tools,
                "tool_outputs": trace.tool_outputs,
                "evidence": trace.evidence,
                "handoff_to": trace.handoff_to,
                "unresolved_questions": trace.unresolved_questions,
                "model_role": trace.model_role,
                "model_invoked": trace.model_invoked,
                "model_finding": trace.model_finding,
                "model_completion_reason": trace.model_completion_reason,
                "execution_mode": trace.execution_mode,
                "replanning_events": trace.replanning_events,
            }
            for trace in runtime.traces
        )
        trace_sink.extend({
            "agent": "Enterprise Intelligence Supervisor",
            "status": "observed",
            "event": event.get("event"),
            "model_role": "supervisor",
            "model_invoked": True,
            "selected_tools": event.get("tasks", event.get("additional_tools", [])),
            "tool_outputs": [],
            "evidence": [],
            "handoff_to": [],
            "unresolved_questions": [],
            "replanning_events": [event.get("event", "supervisor_event")],
        } for event in runtime.model_events)
    return [results[name] for name in [tool_to_agent[selection.tool] for selection in selections]]


def runtime_catalog() -> dict[str, Any]:
    runtime = build_agent_runtime(os.getenv("WRI_AGENT_MODE", "simulation").lower())
    return runtime.catalog()


def runtime_trace() -> list[dict[str, Any]]:
    return []


__all__ = [
    "EVENT_POLICIES",
    "MetaModelPlanner",
    "run_investigation",
    "validate_model_tool_request",
    "validate_tool_request",
    "runtime_catalog",
    "runtime_trace",
]
