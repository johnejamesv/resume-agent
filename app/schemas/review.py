from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reviewer_type: Literal["factual", "adversarial", "hiring_manager"]
    severity: Literal["hard_fail", "soft_suggestion", "info"]
    target_section: str | None = None
    issue_type: str
    finding: str
    suggested_action: str | None = None
    evidence_ref: str | None = None


class ArbitrationDecision(BaseModel):
    finding_id: str
    action: Literal["accept", "revise", "flag_for_user", "dismiss"]
    rationale: str
    revised_text: str | None = None
