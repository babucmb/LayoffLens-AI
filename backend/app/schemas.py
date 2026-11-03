from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delay_months: float = Field(1.0, ge=0, le=6)
    conversion: float = Field(0.82, ge=0.4, le=1.1)
    infra_change: float = Field(0.12, ge=-0.3, le=0.8)
    hiring_delay: float = Field(0, ge=0, le=3)
    mobility: float = Field(0.0, ge=0, le=10)


class ScenarioSimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_type: Literal["baseline", "upside", "downside", "stress", "intervention", "alternative"] = "baseline"
    horizon_days: Literal[30, 90, 180, 365] = 90
    assumptions: dict[str, float] = Field(default_factory=dict)
    intervention_id: str | None = Field(default=None, max_length=80)
    constraints: dict[str, float] = Field(default_factory=dict)


class ScenarioEvaluation(BaseModel):
    scenario_id: str
    scenario_type: Literal["baseline", "downside", "intervention", "alternative"]
    calculation_version: str
    units: str
    time_horizon: str
    estimated_cost: float | None
    gross_savings: float | None
    net_savings: float | None
    feasibility: Literal["feasible", "infeasible", "insufficient_data"]
    evaluation_status: Literal["evaluated", "insufficient_data"]
    explanation: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result: dict[str, object] = Field(default_factory=dict)


class SensitivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter: Literal["delay_months", "conversion", "infra_change", "hiring_delay", "mobility"]
    low: float
    high: float


class OutcomeComparison(BaseModel):
    outcome_id: str
    investigation_id: str
    category: Literal["capacity", "revenue", "delivery", "other"]
    status: Literal["comparable", "not_comparable", "insufficient_data"]
    observed_value: float | None
    projected_value: float | None
    difference: float | None
    unit: str | None
    explanation: str


class BriefOutput(BaseModel):
    changed: str
    why_it_matters: str
    evidence: list[str] = Field(min_length=1)
    uncertainty: str
    options: list[str] = Field(min_length=1)
    human_review_next: str


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: Literal["accepted", "rejected", "needs_evidence"]
    rationale: str = Field(min_length=3, max_length=1000)
    investigation_id: str | None = Field(default=None, min_length=1, max_length=100)
    scenario_id: str | None = Field(default=None, min_length=1, max_length=100)


class ReviewTransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["open", "in_review", "accepted", "rejected", "needs_evidence", "closed"]
    rationale: str = Field(default="", max_length=1000)


class ReviewAssignmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    role: Literal["reviewer", "operator", "admin"] = "reviewer"


class ReviewCommentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str = Field(min_length=1, max_length=2000)


class EvidenceRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=3, max_length=1000)
    due_on: str | None = Field(default=None, max_length=40)


class ReviewEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[str] = Field(min_length=1, max_length=100)


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal[
        "project_delay", "infrastructure_cost", "revenue_decline",
        "ai_transformation", "combined_business_stress",
    ] = "project_delay"
    budget: int = Field(6, ge=1, le=6)
    event_id: str | None = Field(default=None, min_length=1, max_length=100)


class EventReplayRequest(InvestigationRequest):
    event_id: str | None = Field(default=None, min_length=1, max_length=100)
    snapshot_id: str | None = Field(default=None, min_length=1, max_length=100)


class OutcomeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(min_length=1, max_length=100)
    category: Literal["capacity", "revenue", "delivery", "other"]
    value: float | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    unit: str | None = Field(default=None, max_length=50)
    observed_on: str = Field(min_length=10, max_length=40)
    evidence_source: str = Field(min_length=3, max_length=500)
    provenance: Literal["explicitly_supplied", "synthetic_fixture"] = "explicitly_supplied"


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["capacity", "revenue"] | None = None
    minimum_samples: int = Field(default=2, ge=1, le=1000)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class AgentResult(BaseModel):
    agent: str
    status: Literal["completed", "failed"]
    evidence: list[str]
    result: dict[str, object] = Field(default_factory=dict)
    error: str | None = None
    reason: str = ""
    inputs: list[str] = Field(default_factory=list)
