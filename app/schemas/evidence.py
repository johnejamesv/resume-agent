from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str | None = None
    content: str
    source_type: Literal[
        "resume",
        "transcript",
        "brag_doc",
        "linkedin",
        "notes",
        "performance_review",
        "project_summary",
        "other",
    ]
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    source_excerpt: str
    category: Literal[
        "role",
        "project",
        "achievement",
        "skill",
        "education",
        "certification",
        "metric",
        "leadership",
        "other",
    ]
    claim: str
    date_context: str | None = None
    entities: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
