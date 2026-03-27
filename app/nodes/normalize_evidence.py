from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceItem, SourceDocument
from app.services.deterministic import build_candidate_profile, extract_evidence_fallback
from app.services.llm import complete_structured, llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState

SYSTEM_PROMPT = (
    "You are an expert resume analyst. Extract structured evidence items from "
    "the provided text. Each item should capture a distinct claim about the "
    "candidate's experience: roles held, projects built, achievements earned, "
    "skills demonstrated, education, certifications, quantitative metrics, or "
    "leadership signals. Be precise — quote short excerpts from the source text "
    "and assign a confidence score (0.0–1.0) based on specificity."
)


class EvidenceItemExtract(BaseModel):
    """Single evidence item as extracted by the LLM."""

    source_excerpt: str
    category: Literal[
        "role", "project", "achievement", "skill",
        "education", "certification", "metric", "leadership", "other",
    ]
    claim: str
    date_context: str | None = None
    entities: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class EvidenceExtractionResult(BaseModel):
    """Wrapper model for structured LLM response."""

    items: list[EvidenceItemExtract]


def _is_job_description(doc: SourceDocument) -> bool:
    return doc.source_type == "other" and bool(
        doc.filename and "job_description" in doc.filename.lower()
    )


async def _extract_with_llm(doc: SourceDocument) -> list[EvidenceItem]:
    prompt = (
        f"Extract all evidence items from this document.\n\n"
        f"--- SOURCE ({doc.source_type}: {doc.filename or 'untitled'}) ---\n"
        f"{doc.content}\n--- END ---"
    )
    result = await complete_structured(
        prompt,
        response_model=EvidenceExtractionResult,
        system=SYSTEM_PROMPT,
        temperature=0.3,
    )
    return [
        EvidenceItem(
            source_id=doc.id,
            source_excerpt=ext.source_excerpt,
            category=ext.category,
            claim=ext.claim,
            date_context=ext.date_context,
            entities=ext.entities,
            confidence=ext.confidence,
        )
        for ext in result.items
    ]


async def run_normalize_evidence(state: WorkflowState) -> dict:
    """Extract structured evidence from each candidate source document."""
    sources = state.get("sources", [])
    errors: list[str] = list(state.get("errors", []))
    all_evidence: list[EvidenceItem] = []

    candidate_sources = [s for s in sources if not _is_job_description(s)]

    for doc in candidate_sources:
        used_fallback = True
        if llm_available():
            try:
                all_evidence.extend(await _extract_with_llm(doc))
                used_fallback = False
            except Exception as exc:
                errors.append(
                    f"normalize_evidence: LLM extraction failed for "
                    f"'{doc.filename}': {exc}"
                )

        if used_fallback:
            all_evidence.extend(extract_evidence_fallback(doc))

    profile = build_candidate_profile(all_evidence, candidate_sources)

    print(
        f"[normalize_evidence] Extracted {len(all_evidence)} evidence items "
        f"from {len(candidate_sources)} sources"
    )

    return {
        "evidence": all_evidence,
        "candidate_profile": profile,
        "errors": errors,
        "current_stage": "normalize_evidence",
    }
