from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from app.schemas.candidate import CandidateProfile, GapQuestion
from app.schemas.evidence import EvidenceItem
from app.services.deterministic import build_gap_questions_fallback
from app.services.llm import complete_structured, llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState

SYSTEM_PROMPT = (
    "You are a senior resume reviewer. Given a candidate's evidence items and "
    "profile summary, identify gaps that would weaken a resume. Look for:\n"
    "- Missing quantitative metrics (revenue, users, percentages)\n"
    "- Vague or missing date ranges\n"
    "- Unclear team size or scope of ownership\n"
    "- Missing impact statements (business outcomes, customer value)\n"
    "- Skills claimed without supporting evidence\n"
    "- Gaps in employment timeline\n"
    "- Missing education details\n"
    "For each gap, write a specific follow-up question the candidate should answer."
)


class GapQuestionExtract(BaseModel):
    """Single gap question as identified by the LLM."""

    question: str
    category: str
    priority: Literal["critical", "important", "nice_to_have"]


class GapAnalysisResult(BaseModel):
    """Wrapper model for structured LLM response."""

    gaps: list[GapQuestionExtract]


def _format_evidence_summary(
    evidence: list[EvidenceItem],
    profile: CandidateProfile | None,
) -> str:
    """Build a text summary of the candidate for the LLM prompt."""
    parts: list[str] = []

    if profile:
        if profile.name:
            parts.append(f"Name: {profile.name}")
        if profile.skills:
            parts.append(f"Skills: {', '.join(profile.skills)}")
        if profile.certifications:
            parts.append(f"Certifications: {', '.join(profile.certifications)}")

    parts.append(f"\n--- {len(evidence)} Evidence Items ---")
    for item in evidence:
        line = f"[{item.category}] {item.claim}"
        if item.date_context:
            line += f" ({item.date_context})"
        parts.append(line)

    return "\n".join(parts)


async def run_gap_finder(state: WorkflowState) -> dict:
    """Identify missing or weak information in the candidate profile."""
    evidence: list[EvidenceItem] = state.get("evidence", [])
    profile: CandidateProfile | None = state.get("candidate_profile")
    errors: list[str] = list(state.get("errors", []))

    if not evidence:
        print("[gap_finder] No evidence to analyse — skipping")
        return {"gaps": [], "errors": errors, "current_stage": "gap_finder"}

    gaps: list[GapQuestion] = []
    if llm_available():
        summary = _format_evidence_summary(evidence, profile)
        prompt = (
            "Analyse this candidate's evidence and identify information gaps "
            "that should be filled before writing a strong resume.\n\n"
            f"{summary}"
        )

        try:
            result = await complete_structured(
                prompt,
                response_model=GapAnalysisResult,
                system=SYSTEM_PROMPT,
                temperature=0.3,
            )
            for ext in result.gaps:
                gaps.append(
                    GapQuestion(
                        id=str(uuid.uuid4()),
                        question=ext.question,
                        category=ext.category,
                        priority=ext.priority,
                    )
                )
        except Exception as exc:
            errors.append(f"gap_finder: LLM analysis failed: {exc}")

    if not gaps:
        gaps = build_gap_questions_fallback(evidence, profile)

    print(f"[gap_finder] Found {len(gaps)} gaps")

    return {
        "gaps": gaps,
        "errors": errors,
        "current_stage": "gap_finder",
    }
