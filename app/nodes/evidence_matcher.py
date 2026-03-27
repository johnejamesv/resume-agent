from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.schemas import CoverageEntry, CoverageMap
from app.services.deterministic import build_coverage_map_fallback
from app.services.llm import complete_structured, llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState

SYSTEM_PROMPT = (
    "You are a resume strategist. Given a list of candidate evidence items and "
    "job requirements, determine which evidence supports each requirement. "
    "Rate each match as strong, weak, adjacent, or missing."
)


class _LLMCoverageEntry(BaseModel):
    requirement_id: str
    strength: str = Field(description="strong, weak, adjacent, or missing")
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class _LLMCoverageResponse(BaseModel):
    entries: list[_LLMCoverageEntry] = Field(default_factory=list)


def _build_prompt(evidence_block: str, requirements_block: str) -> str:
    return (
        "Match candidate evidence to job requirements.\n\n"
        f"## Evidence\n{evidence_block}\n\n"
        f"## Requirements\n{requirements_block}\n\n"
        "For EVERY requirement, provide a coverage entry with the requirement_id, "
        "a strength rating (strong/weak/adjacent/missing), the list of supporting "
        "evidence_ids (empty if missing), and brief notes explaining the match."
    )


def _compute_score(entries: list[CoverageEntry]) -> float:
    total = len(entries)
    if total == 0:
        return 0.0
    points = sum(
        {"strong": 1.0, "weak": 0.5, "adjacent": 0.25, "missing": 0.0}[e.strength]
        for e in entries
    )
    return round(points / total, 2)


async def run_evidence_matcher(state: WorkflowState) -> dict:
    """Map evidence items to job requirements, producing CoverageMap objects."""
    print("[evidence_matcher] Processing...")

    job_briefs = state.get("job_briefs", [])
    evidence = state.get("evidence", [])
    errors: list[str] = list(state.get("errors", []))

    if not job_briefs:
        print("[evidence_matcher] No job briefs found.")
        return {"coverage_maps": [], "current_stage": "evidence_matcher"}

    evidence_block = "\n".join(
        f"- [{e.id}] ({e.category}) {e.claim}" for e in evidence
    )

    coverage_maps: list[CoverageMap] = []

    for brief in job_briefs:
        all_reqs = brief.must_have + brief.preferred
        if not all_reqs:
            coverage_maps.append(CoverageMap(job_id=brief.job_title, entries=[]))
            continue

        cmap: CoverageMap | None = None
        if llm_available():
            req_block = "\n".join(
                f"- [{r.id}] ({r.category}) {r.text}" for r in all_reqs
            )
            prompt = _build_prompt(evidence_block, req_block)

            try:
                result = await complete_structured(
                    prompt, _LLMCoverageResponse, system=SYSTEM_PROMPT, temperature=0.3,
                )
                entries = [
                    CoverageEntry(
                        requirement_id=e.requirement_id,
                        strength=e.strength,
                        evidence_ids=e.evidence_ids,
                        notes=e.notes,
                    )
                    for e in result.entries
                    if e.requirement_id in {req.id for req in all_reqs}
                ]
                seen_requirement_ids = {entry.requirement_id for entry in entries}
                for req in all_reqs:
                    if req.id not in seen_requirement_ids:
                        entries.append(
                            CoverageEntry(
                                requirement_id=req.id,
                                strength="missing",
                                evidence_ids=[],
                                notes="No coverage entry returned by LLM",
                            )
                        )

                score = _compute_score(entries)
                cmap = CoverageMap(job_id=brief.job_title, entries=entries, coverage_score=score)
            except Exception as exc:
                msg = f"[evidence_matcher] LLM error for '{brief.job_title}': {exc}"
                print(msg)
                errors.append(msg)

        if cmap is None:
            cmap = build_coverage_map_fallback(brief, evidence)

        covered = sum(1 for entry in cmap.entries if entry.strength != "missing")
        coverage_maps.append(cmap)

        print(
            f"[evidence_matcher] Job '{brief.job_title}': "
            f"{covered}/{len(all_reqs)} requirements covered, score: {cmap.coverage_score}"
        )

    print(f"[evidence_matcher] Produced {len(coverage_maps)} coverage map(s).")
    return {
        "coverage_maps": coverage_maps,
        "current_stage": "evidence_matcher",
        "errors": errors,
    }
