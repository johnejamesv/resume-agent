from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.review import ArbitrationDecision, ReviewFinding


class BulletCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_ids: list[str]
    text: str
    variant: Literal[
        "metric_forward",
        "technical_depth",
        "leadership_forward",
        "business_impact",
        "balanced",
    ]
    target_requirement_id: str | None = None
    provenance_notes: str | None = None


class ResumeSection(BaseModel):
    heading: str
    bullets: list[BulletCandidate] = Field(default_factory=list)
    order: int = 0


class ResumeDraft(BaseModel):
    candidate_name: str
    target_job: str
    sections: list[ResumeSection] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    arbitration_decisions: list[ArbitrationDecision] = Field(default_factory=list)
    version: int = 1


class RunArtifact(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime
    completed_at: datetime | None = None
    input_sources: list[str] = Field(default_factory=list)
    target_jobs: list[str] = Field(default_factory=list)
    final_draft: ResumeDraft | None = None
    all_findings: list[ReviewFinding] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
