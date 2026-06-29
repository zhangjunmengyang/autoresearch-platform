"""Pydantic contracts for the public AutoResearch REST API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal[
    "planned",
    "queued",
    "claimed",
    "running",
    "completed",
    "failed",
    "rejected",
    "superseded",
    "blocked",
    "degraded",
    "archived",
]

SourceKind = Literal["paper", "url", "dataset", "repo", "note", "artifact_ref", "human_command", "runtime_input"]
EventKind = Literal[
    "observation",
    "decision",
    "tool_run",
    "human_instruction",
    "runtime_event",
    "blocker",
]
DecisionKind = Literal["accept", "reject", "continue", "block", "supersede", "archive"]
EvidenceStance = Literal["supports", "contradicts", "mixed", "inconclusive", "replicates", "fails_to_replicate"]
EvidenceKind = Literal[
    "source",
    "experiment",
    "benchmark_run",
    "artifact",
    "review",
    "decision",
    "replication",
    "human_assessment",
]


class RecordModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SourceCreate(RecordModel):
    kind: SourceKind
    title: str
    uri: str | None = None
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class InsightCreate(RecordModel):
    title: str
    body: str
    insight_type: str = "finding"
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class HypothesisCreate(RecordModel):
    title: str
    hypothesis: str
    expected_effect: str = ""
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    rejection_criteria: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    insight_refs: list[str] = Field(default_factory=list)
    status: Status = "planned"


class ResearchProgramCreate(RecordModel):
    title: str
    goal: str
    domain: str = "general"
    constraints: list[str] = Field(default_factory=list)
    status: Status = "planned"


class ResearchQuestionCreate(RecordModel):
    program_id: str | None = None
    question: str
    rationale: str = ""
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    status: Status = "planned"


class MethodCardCreate(RecordModel):
    name: str
    domain: str = "general"
    when_to_use: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    status: Status = "planned"


class ProtocolCreate(RecordModel):
    question_id: str
    method_id: str | None = None
    hypothesis_id: str | None = None
    one_change: str
    controls: list[str] = Field(default_factory=list)
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    rejection_criteria: dict[str, Any] = Field(default_factory=dict)
    artifact_requirements: list[str] = Field(default_factory=list)
    status: Status = "planned"


class IntakeCreate(RecordModel):
    title: str
    rationale: str = ""
    priority: int = Field(3, ge=0, le=5)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    insight_refs: list[str] = Field(default_factory=list)
    hypothesis_refs: list[str] = Field(default_factory=list)
    human_constraints: list[str] = Field(default_factory=list)
    requested_by: str = "human"
    status: Status = "queued"


class SessionCreate(RecordModel):
    session_id: str | None = None
    title: str
    target: dict[str, Any] = Field(default_factory=dict)
    memory_context: dict[str, Any] = Field(default_factory=dict)
    primary_path: str = ""
    secondary_path_if_needed: list[str] = Field(default_factory=list)
    information_gain: str = ""
    human_constraints: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    status: Status = "planned"


class ResearchRoundCreate(RecordModel):
    title: str
    session_id: str | None = None
    proposal: str
    objective: str = ""
    worktree: dict[str, Any] = Field(default_factory=dict)
    implementation_refs: list[dict[str, Any]] = Field(default_factory=list)
    experiment_refs: list[dict[str, Any]] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    decision_refs: list[dict[str, Any]] = Field(default_factory=list)
    retrospective: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    status: Status = "planned"


class ResearchRoundPatch(RecordModel):
    title: str | None = None
    proposal: str | None = None
    objective: str | None = None
    worktree: dict[str, Any] | None = None
    implementation_refs: list[dict[str, Any]] | None = None
    experiment_refs: list[dict[str, Any]] | None = None
    artifact_refs: list[dict[str, Any]] | None = None
    evidence_refs: list[dict[str, Any]] | None = None
    decision_refs: list[dict[str, Any]] | None = None
    retrospective: dict[str, Any] | None = None
    runtime: dict[str, Any] | None = None
    status: Status | None = None


class EventCreate(RecordModel):
    event_type: EventKind
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = "external-runtime"


class ExperimentCreate(RecordModel):
    hypothesis: str
    experiment_type: str = "benchmark"
    expected_effect: str = ""
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    rejection_criteria: dict[str, Any] = Field(default_factory=dict)
    one_change: str = ""
    forbidden_scope: list[str] = Field(default_factory=list)
    status: Status = "planned"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentPatch(RecordModel):
    status: Status | None = None
    result_summary: str | None = None
    metrics: dict[str, Any] | None = None
    artifact_refs: list[dict[str, Any]] | None = None
    retrospective: dict[str, Any] | None = None


class ArtifactCreate(RecordModel):
    artifact_type: str
    title: str
    uri: str | None = None
    sha256: str | None = None
    mime_type: str = "application/octet-stream"
    size_bytes: int | None = Field(None, ge=0)
    storage: Literal["local", "s3", "gcs", "http", "external"] = "external"
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    read_hint: dict[str, Any] = Field(default_factory=dict)


class SessionClose(RecordModel):
    status: Status = "completed"
    retrospective: dict[str, Any]
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    generated_intake_item_ids: list[str] = Field(default_factory=list)


class BenchmarkCreate(RecordModel):
    name: str
    domain: str = "general"
    description: str = ""
    metric_schema: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    artifact_requirements: list[dict[str, Any]] = Field(default_factory=list)
    external_runner: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    status: Status = "planned"


class BenchmarkRunCreate(RecordModel):
    benchmark_id: str
    session_id: str | None = None
    experiment_id: str | None = None
    runtime: dict[str, Any] = Field(default_factory=dict)
    status: Status = "running"
    scores: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRunPatch(RecordModel):
    status: Status | None = None
    scores: dict[str, Any] | None = None
    artifact_refs: list[dict[str, Any]] | None = None
    error: str | None = None
    provenance: dict[str, Any] | None = None


class ReviewCreate(RecordModel):
    subject: dict[str, Any]
    reviewer: dict[str, Any] = Field(default_factory=dict)
    verdict: Status = "completed"
    score: float | None = Field(None, ge=0, le=100)
    comments: str = ""
    concerns: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceRecordCreate(RecordModel):
    claim: str
    stance: EvidenceStance
    evidence_kind: EvidenceKind
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    subject: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    quality: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    recorded_by: dict[str, Any] = Field(default_factory=dict)
    status: Status = "completed"


class DecisionCreate(RecordModel):
    subject: dict[str, Any]
    decision: DecisionKind
    rationale: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    criteria: dict[str, Any] = Field(default_factory=dict)
    next_steps: list[str] = Field(default_factory=list)
    decided_by: dict[str, Any] = Field(default_factory=dict)
    status: Status = "completed"


class ExperienceQuery(RecordModel):
    query: str = ""
    topics: list[str] = Field(default_factory=list)
    limit: int = Field(20, ge=1, le=100)


class ExperienceCurationRequest(RecordModel):
    action: Literal["create", "update", "reject", "supersede", "topic_summary"] = "create"
    runtime: dict[str, Any]
    experience: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    human_readable: bool = True


class ExperienceTopicSummaryUpdate(RecordModel):
    title: str
    summary: str
    status: Status = "completed"
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)


class ListEnvelope(RecordModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    sort: str


class ApiEnvelope(RecordModel):
    data: Any
    warnings: list[str] = Field(default_factory=list)
