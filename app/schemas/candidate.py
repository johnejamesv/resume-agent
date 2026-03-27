from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceItem


class GapQuestion(BaseModel):
    id: str
    question: str
    category: str
    priority: Literal["critical", "important", "nice_to_have"]
    resolved: bool = False
    answer: str | None = None


class CandidateProfile(BaseModel):
    name: str | None = None
    email: str | None = None
    location: str | None = None
    summary: str | None = None
    work_history: list[EvidenceItem] = Field(default_factory=list)
    achievements: list[EvidenceItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[EvidenceItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    project_evidence: list[EvidenceItem] = Field(default_factory=list)
    unresolved_gaps: list[GapQuestion] = Field(default_factory=list)
