from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


EVENT_POLICIES: dict[str, tuple[str, ...]] = {
    "project_delay": (
        "Project demand analyst",
        "Workforce capacity analyst",
        "Scenario analyst",
        "Preventive action planner",
        "Finance analyst",
        "Evidence and policy reviewer",
    ),
    "infrastructure_cost": (
        "Finance analyst",
        "Scenario analyst",
        "Preventive action planner",
        "Project demand analyst",
        "Workforce capacity analyst",
        "Evidence and policy reviewer",
    ),
    "revenue_decline": (
        "Finance analyst",
        "Sales and demand analyst",
        "Project demand analyst",
        "Workforce capacity analyst",
        "Forecast and risk analyst",
        "Evidence and policy reviewer",
    ),
    "ai_transformation": (
        "AI transformation analyst",
        "Project demand analyst",
        "Workforce capacity analyst",
        "Forecast and risk analyst",
        "Evidence and policy reviewer",
    ),
    "combined_business_stress": (
        "Finance analyst",
        "Sales and demand analyst",
        "Project demand analyst",
        "Infrastructure and operations analyst",
        "Forecast and risk analyst",
        "Evidence and policy reviewer",
    ),
}

TOOL_NAMES = {
    "finance_analysis",
    "project_analysis",
    "capacity_analysis",
    "scenario_analysis",
    "action_plan",
    "evidence_review",
    "sales_demand_analysis",
    "ai_transformation_analysis",
    "forecast_risk_analysis",
    "infrastructure_operations_analysis",
    "external_research",
}


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(pattern="^tool_request$")
    tool: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class InvestigationContext:
    event_type: str
    budget: int
    completed_tools: tuple[str, ...] = ()
    evidence_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ToolSelection:
    tool: str
    reason: str
    required_dependencies: tuple[str, ...] = ()


class InvestigationPlanner(Protocol):
    name: str

    def select(self, context: InvestigationContext) -> list[ToolSelection]:
        ...


_AGENT_TO_TOOL = {
    "Finance analyst": "finance_analysis",
    "Project demand analyst": "project_analysis",
    "Workforce capacity analyst": "capacity_analysis",
    "Scenario analyst": "scenario_analysis",
    "Preventive action planner": "action_plan",
    "Evidence and policy reviewer": "evidence_review",
    "Sales and demand analyst": "sales_demand_analysis",
    "AI transformation analyst": "ai_transformation_analysis",
    "Forecast and risk analyst": "forecast_risk_analysis",
    "Infrastructure and operations analyst": "infrastructure_operations_analysis",
}


class DeterministicPlanner:
    name = "deterministic-policy-v1"

    def select(self, context: InvestigationContext) -> list[ToolSelection]:
        if context.event_type not in EVENT_POLICIES:
            raise ValueError(f"Unsupported event type: {context.event_type}")
        if not 1 <= context.budget <= 6:
            raise ValueError("Investigation budget must be between 1 and 6.")
        completed = set(context.completed_tools)
        selections: list[ToolSelection] = []
        for agent in EVENT_POLICIES[context.event_type][: context.budget]:
            tool = _AGENT_TO_TOOL[agent]
            if tool in completed:
                continue
            dependencies: tuple[str, ...] = ()
            if tool == "capacity_analysis":
                dependencies = ("project_analysis",)
            elif tool == "action_plan":
                dependencies = ("scenario_analysis",)
            elif tool == "evidence_review":
                # Review is a gate after whatever bounded specialist set was
                # selected; it must not require tools that were not planned.
                dependencies = ()
            selections.append(
                ToolSelection(
                    tool=tool,
                    reason=f"{agent} selected by {self.name} for {context.event_type}.",
                    required_dependencies=dependencies,
                )
            )
        return selections


class MetaModelPlanner:
    """Validates a model-proposed tool request without executing it."""

    name = "meta-model-planner"

    def __init__(self, allowed_tools: set[str] | None = None):
        self.allowed_tools = allowed_tools or TOOL_NAMES

    def select_request(
        self,
        response: dict[str, Any],
        context: InvestigationContext,
        arguments: dict[str, Any] | None = None,
    ) -> ToolSelection:
        request = ToolRequest.model_validate(response)
        if request.tool not in self.allowed_tools:
            raise ValueError(f"Unsupported investigation tool: {request.tool}")
        if request.tool in context.completed_tools:
            raise ValueError(f"Duplicate investigation tool: {request.tool}")
        if len(context.completed_tools) >= context.budget:
            raise ValueError("Investigation step budget exhausted.")
        required = ("project_analysis",) if request.tool == "capacity_analysis" else ()
        missing = [tool for tool in required if tool not in context.completed_tools]
        if missing:
            raise ValueError(f"Tool dependencies are not complete: {', '.join(missing)}")
        requested_arguments = arguments if arguments is not None else request.arguments
        if not isinstance(requested_arguments, dict):
            raise ValueError("Tool arguments must be an object.")
        if any(str(value).startswith(("shell:", "sql:", "file:")) for value in requested_arguments.values()):
            raise ValueError("Arbitrary shell, SQL, and filesystem requests are not permitted.")
        return ToolSelection(
            tool=request.tool,
            reason="Validated structured request from optional Meta planner.",
            required_dependencies=required,
        )


def validate_model_tool_request(response: dict[str, Any], allowed: set[str]) -> tuple[str, dict[str, Any]]:
    request = ToolRequest.model_validate(response)
    if request.tool not in allowed:
        raise ValueError(f"Unsupported investigation tool: {request.tool}")
    return request.tool, request.arguments
