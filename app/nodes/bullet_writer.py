from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceItem
from app.schemas.job import CoverageEntry, CoverageMap, JobBrief, RequirementItem
from app.schemas.resume import BulletCandidate
from app.services.deterministic import build_bullet_candidates_fallback
from app.services.llm import complete_structured, llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState

SYSTEM_PROMPT = (
    "You are an expert resume writer. Given evidence about a candidate and a "
    "specific job requirement, generate concise, impactful resume bullets. "
    "Each bullet should lead with a strong action verb and include measurable "
    "results where available. Stay grounded in the provided evidence — never "
    "fabricate claims."
)


class GeneratedBullet(BaseModel):
    """A single bullet produced by the LLM."""

    text: str
    variant: Literal[
        "metric_forward", "technical_depth", "leadership_forward",
        "business_impact", "balanced",
    ]
    provenance_notes: str | None = None


class BulletGenerationResult(BaseModel):
    """Wrapper for structured LLM output."""

    bullets: list[GeneratedBullet] = Field(default_factory=list)


def _build_evidence_map(evidence: list[EvidenceItem]) -> dict[str, EvidenceItem]:
    """Index evidence items by ID for fast lookup."""
    return {item.id: item for item in evidence}


def _build_requirement_map(brief: JobBrief) -> dict[str, RequirementItem]:
    """Index all requirements from a job brief by ID."""
    reqs: dict[str, RequirementItem] = {}
    for r in brief.must_have + brief.preferred:
        reqs[r.id] = r
    return reqs


def _build_prompt_for_entry(
    entry: CoverageEntry,
    evidence_items: list[EvidenceItem],
    requirement: RequirementItem | None,
) -> str:
    """Build the LLM prompt for a single coverage entry."""
    evidence_block = "\n\n".join(
        f"Evidence [{e.category}] (confidence {e.confidence}):\n"
        f"  Claim: {e.claim}\n"
        f"  Excerpt: \"{e.source_excerpt}\""
        for e in evidence_items
    )
    req_text = requirement.text if requirement else "General candidate strength"
    return (
        f"Target requirement: {req_text}\n"
        f"Match strength: {entry.strength}\n\n"
        f"{evidence_block}\n\n"
        f"Generate 2-3 resume bullet variants from this evidence. Include:\n"
        f"- metric_forward: leads with a quantitative result\n"
        f"- balanced: concise all-around bullet\n"
        f"- One of: technical_depth, leadership_forward, or business_impact "
        f"(whichever best fits the evidence)\n"
        f"Each bullet should be one sentence, under 25 words."
    )


def _build_prompt_for_untied(evidence_items: list[EvidenceItem]) -> str:
    """Build a prompt for evidence not tied to any requirement."""
    evidence_block = "\n\n".join(
        f"Evidence [{e.category}] (confidence {e.confidence}):\n"
        f"  Claim: {e.claim}\n"
        f"  Excerpt: \"{e.source_excerpt}\""
        for e in evidence_items
    )
    return (
        f"The following evidence highlights general candidate strengths not "
        f"tied to a specific requirement.\n\n"
        f"{evidence_block}\n\n"
        f"Generate 1-2 concise resume bullets (balanced or metric_forward "
        f"variant). Each should be one sentence, under 25 words."
    )


async def run_bullet_writer(state: WorkflowState) -> dict:
    """Generate resume bullet candidates from evidence and coverage maps."""
    print("[bullet_writer] Processing...")

    evidence: list[EvidenceItem] = state.get("evidence", [])
    coverage_maps: list[CoverageMap] = state.get("coverage_maps", [])
    job_briefs: list[JobBrief] = state.get("job_briefs", [])
    errors: list[str] = list(state.get("errors", []))

    if not evidence:
        errors.append("bullet_writer: no evidence items available")
        print("[bullet_writer] No evidence items — skipping.")
        return {"bullet_candidates": [], "errors": errors, "current_stage": "bullet_writer"}

    if not coverage_maps or not job_briefs:
        errors.append("bullet_writer: no coverage maps or job briefs available")
        print("[bullet_writer] No coverage maps or job briefs — skipping.")
        return {"bullet_candidates": [], "errors": errors, "current_stage": "bullet_writer"}

    ev_map = _build_evidence_map(evidence)
    brief = job_briefs[0]
    coverage = coverage_maps[0]
    req_map = _build_requirement_map(brief)

    all_bullets: list[BulletCandidate] = []
    covered_evidence_ids: set[str] = set()

    if llm_available():
        # Generate bullets for each coverage entry with usable evidence
        for entry in coverage.entries:
            if entry.strength == "missing":
                continue
            matched_evidence = [ev_map[eid] for eid in entry.evidence_ids if eid in ev_map]
            if not matched_evidence:
                continue

            covered_evidence_ids.update(entry.evidence_ids)
            requirement = req_map.get(entry.requirement_id)
            prompt = _build_prompt_for_entry(entry, matched_evidence, requirement)

            try:
                result = await complete_structured(
                    prompt,
                    response_model=BulletGenerationResult,
                    system=SYSTEM_PROMPT,
                    temperature=0.5,
                )
                for gen in result.bullets:
                    bullet = BulletCandidate(
                        evidence_ids=[e.id for e in matched_evidence],
                        text=gen.text,
                        variant=gen.variant,
                        target_requirement_id=entry.requirement_id,
                        provenance_notes=gen.provenance_notes,
                    )
                    all_bullets.append(bullet)
            except Exception as exc:
                errors.append(
                    f"bullet_writer: LLM failed for requirement "
                    f"'{entry.requirement_id}': {exc}"
                )

        # Generate bullets for untied evidence (strong general points)
        untied = [e for e in evidence if e.id not in covered_evidence_ids and e.confidence >= 0.6]
        if untied:
            prompt = _build_prompt_for_untied(untied[:5])  # cap to avoid prompt bloat
            try:
                result = await complete_structured(
                    prompt,
                    response_model=BulletGenerationResult,
                    system=SYSTEM_PROMPT,
                    temperature=0.5,
                )
                for gen in result.bullets:
                    bullet = BulletCandidate(
                        evidence_ids=[e.id for e in untied[:5]],
                        text=gen.text,
                        variant=gen.variant,
                        target_requirement_id=None,
                        provenance_notes=gen.provenance_notes,
                    )
                    all_bullets.append(bullet)
            except Exception as exc:
                errors.append(f"bullet_writer: LLM failed for untied evidence: {exc}")

    if not all_bullets:
        all_bullets = build_bullet_candidates_fallback(coverage, brief, evidence)

    print(f"[bullet_writer] Generated {len(all_bullets)} bullet candidates.")
    return {
        "bullet_candidates": all_bullets,
        "errors": errors,
        "current_stage": "bullet_writer",
    }
