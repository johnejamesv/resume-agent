from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas import JobBrief, RequirementItem
from app.schemas.evidence import SourceDocument
from app.services.deterministic import parse_job_brief_fallback
from app.services.llm import complete_structured, llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState

SYSTEM_PROMPT = (
    "You are an expert recruiter. Extract structured job requirements from the "
    "provided job description. Be thorough — capture every stated requirement."
)


class _ParsedRequirement(BaseModel):
    text: str
    category: str = Field(description="must_have, preferred, or bonus")
    keywords: list[str] = Field(default_factory=list)


class _ParsedJob(BaseModel):
    job_title: str
    company: str
    seniority: str | None = None
    must_have: list[_ParsedRequirement] = Field(default_factory=list)
    preferred: list[_ParsedRequirement] = Field(default_factory=list)
    bonus: list[_ParsedRequirement] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    domain_context: str | None = None


def _to_requirement(parsed: _ParsedRequirement, category: str) -> RequirementItem:
    return RequirementItem(
        id=str(uuid4()),
        text=parsed.text,
        category=category,
        keywords=parsed.keywords,
    )


async def _parse_with_llm(src: SourceDocument) -> JobBrief:
    prompt = (
        f"Parse the following job description and extract all structured "
        f"information.\n\n---\n{src.content}\n---"
    )
    parsed = await complete_structured(
        prompt, _ParsedJob, system=SYSTEM_PROMPT, temperature=0.3,
    )

    return JobBrief(
        job_title=parsed.job_title,
        company=parsed.company,
        seniority=parsed.seniority,
        must_have=[_to_requirement(r, "must_have") for r in parsed.must_have],
        preferred=[_to_requirement(r, "preferred") for r in parsed.preferred]
        + [_to_requirement(r, "bonus") for r in parsed.bonus],
        keywords=parsed.keywords,
        themes=parsed.themes,
        domain_context=parsed.domain_context,
        raw_text=src.content,
    )


async def run_job_parser(state: WorkflowState) -> dict:
    """Parse job description sources into structured JobBrief objects."""
    print("[job_parser] Processing...")

    sources = state.get("sources", [])
    errors: list[str] = list(state.get("errors", []))

    jd_sources = [
        s for s in sources
        if s.source_type == "other" and s.filename and "job_description" in s.filename
    ]

    if not jd_sources:
        print("[job_parser] No job description sources found.")
        return {"job_briefs": [], "current_stage": "job_parser"}

    job_briefs: list[JobBrief] = []
    total_reqs = 0

    for src in jd_sources:
        brief: JobBrief | None = None
        if llm_available():
            try:
                brief = await _parse_with_llm(src)
            except Exception as exc:
                msg = f"[job_parser] LLM error for {src.filename}: {exc}"
                print(msg)
                errors.append(msg)

        if brief is None:
            brief = parse_job_brief_fallback(src)

        job_briefs.append(brief)
        total_reqs += len(brief.must_have) + len(brief.preferred)

    print(
        f"[job_parser] Parsed {len(job_briefs)} job(s), "
        f"{total_reqs} total requirements extracted."
    )
    return {"job_briefs": job_briefs, "current_stage": "job_parser", "errors": errors}
