from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RequirementItem(BaseModel):
    id: str
    text: str
    category: Literal["must_have", "preferred", "bonus"]
    keywords: list[str] = Field(default_factory=list)


class JobBrief(BaseModel):
    job_title: str
    company: str
    url: str | None = None
    seniority: str | None = None
    must_have: list[RequirementItem] = Field(default_factory=list)
    preferred: list[RequirementItem] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    domain_context: str | None = None
    raw_text: str


class CoverageEntry(BaseModel):
    requirement_id: str
    strength: Literal["strong", "weak", "missing", "adjacent"]
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class CoverageMap(BaseModel):
    job_id: str
    entries: list[CoverageEntry] = Field(default_factory=list)
    coverage_score: float | None = None
