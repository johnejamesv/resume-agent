from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from app.schemas.candidate import CandidateProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.job import JobBrief
from app.schemas.resume import BulletCandidate, ResumeDraft, ResumeSection
from app.services.deterministic import dedupe_preserve_order, extract_keywords, normalize_for_matching

if TYPE_CHECKING:
    from app.graph import WorkflowState


VARIANT_PRIORITY = {
    "metric_forward": 0,
    "technical_depth": 1,
    "leadership_forward": 2,
    "business_impact": 3,
    "balanced": 4,
}

SKILL_PRIORITY = [
    "python",
    "fastapi",
    "gcp",
    "cloud run",
    "vertex ai",
    "react",
    "typescript",
    "postgresql",
    "sqlalchemy",
    "docker",
    "terraform",
    "github actions",
    "openai api",
    "claude api",
    "claude code",
    "langgraph",
    "langchain",
    "playwright",
]

SKILL_DISPLAY_NAMES = {
    "python": "Python",
    "fastapi": "FastAPI",
    "gcp": "GCP",
    "cloud run": "Cloud Run",
    "vertex ai": "Vertex AI",
    "react": "React",
    "typescript": "TypeScript",
    "postgresql": "PostgreSQL",
    "sqlalchemy": "SQLAlchemy",
    "github actions": "GitHub Actions",
}


def _unique_bullets(
    bullets: list[BulletCandidate],
    limit: int | None = None,
) -> list[BulletCandidate]:
    seen: set[str] = set()
    result: list[BulletCandidate] = []
    for bullet in bullets:
        key = normalize_for_matching(bullet.text)
        if key in seen:
            continue
        seen.add(key)
        result.append(bullet)
        if limit is not None and len(result) >= limit:
            break
    return result


def _pick_requirement_bullets(
    bullet_candidates: list[BulletCandidate],
    brief: JobBrief,
) -> list[BulletCandidate]:
    grouped: dict[str, list[BulletCandidate]] = defaultdict(list)
    untied: list[BulletCandidate] = []

    for bullet in bullet_candidates:
        if bullet.target_requirement_id:
            grouped[bullet.target_requirement_id].append(bullet)
        else:
            untied.append(bullet)

    selected: list[BulletCandidate] = []
    for requirement in brief.must_have + brief.preferred:
        options = sorted(
            grouped.get(requirement.id, []),
            key=lambda bullet: (
                VARIANT_PRIORITY.get(bullet.variant, 10),
                len(bullet.text.split()),
            ),
        )
        if options:
            selected.append(options[0])

    selected.extend(sorted(untied, key=lambda bullet: len(bullet.text.split()))[:2])
    return _unique_bullets(selected, limit=8)


def _sort_skills(skills: list[str]) -> list[str]:
    def key(skill: str) -> tuple[int, int, str]:
        normalized = normalize_for_matching(skill)
        for idx, preferred in enumerate(SKILL_PRIORITY):
            if preferred in normalized or normalized in preferred:
                return (0, idx, normalized)
        return (1, len(normalized), normalized)

    return sorted(dedupe_preserve_order(skills), key=key)


def _display_skill(skill: str) -> str:
    normalized = normalize_for_matching(skill)
    return SKILL_DISPLAY_NAMES.get(normalized, skill)


def _top_evidence_ids(
    bullets: list[BulletCandidate],
    evidence: list[EvidenceItem],
    limit: int = 4,
) -> list[str]:
    available = {item.id for item in evidence}
    selected_ids: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        for evidence_id in bullet.evidence_ids:
            if evidence_id in available and evidence_id not in seen:
                selected_ids.append(evidence_id)
                seen.add(evidence_id)
            if len(selected_ids) >= limit:
                return selected_ids
    return selected_ids


def _build_summary_section(
    profile: CandidateProfile | None,
    brief: JobBrief,
    evidence: list[EvidenceItem],
    selected_bullets: list[BulletCandidate],
) -> ResumeSection:
    profile = profile or CandidateProfile()
    support_ids = _top_evidence_ids(selected_bullets, evidence, limit=6)
    bullets: list[BulletCandidate] = []

    summary_text = (profile.summary or "").strip()
    if summary_text:
        first_sentence = summary_text.split(". ", 1)[0].strip().rstrip(".") + "."
        bullets.append(
            BulletCandidate(
                evidence_ids=support_ids[:3] or support_ids,
                text=first_sentence,
                variant="balanced",
                provenance_notes="Derived from candidate summary",
            )
        )

    job_text = " ".join(brief.keywords + extract_keywords(brief.raw_text))
    matched_skills = [
        skill for skill in profile.skills
        if normalize_for_matching(skill) in normalize_for_matching(job_text)
    ]
    matched_skills = _sort_skills(matched_skills)
    if not matched_skills:
        matched_skills = _sort_skills(profile.skills)[:5]

    if matched_skills:
        bullets.append(
            BulletCandidate(
                evidence_ids=support_ids[1:5] or support_ids,
                text=(
                    f"Targeting {brief.job_title} roles with hands-on experience in "
                    f"{', '.join(_display_skill(skill) for skill in matched_skills[:5])}."
                ),
                variant="balanced",
                provenance_notes="Tailored summary alignment",
            )
        )

    if not bullets:
        bullets.append(
            BulletCandidate(
                evidence_ids=support_ids,
                text=f"Engineer targeting {brief.job_title} roles with evidence-backed technical experience.",
                variant="balanced",
                provenance_notes="Fallback summary",
            )
        )

    return ResumeSection(
        heading="Professional Summary",
        bullets=_unique_bullets(bullets, 2),
        order=0,
    )


def _build_skills_section(
    profile: CandidateProfile | None,
    brief: JobBrief,
    evidence: list[EvidenceItem],
) -> ResumeSection | None:
    profile = profile or CandidateProfile()
    if not profile.skills:
        return None

    job_text = " ".join(brief.keywords + extract_keywords(brief.raw_text))
    matched_skills = [
        skill for skill in profile.skills
        if normalize_for_matching(skill) in normalize_for_matching(job_text)
    ]
    matched_skills = _sort_skills(matched_skills)
    core_skills = matched_skills[:8] or _sort_skills(profile.skills)[:8]
    if not core_skills:
        return None

    skill_to_ids: dict[str, list[str]] = defaultdict(list)
    for item in evidence:
        if item.category == "skill":
            skill_to_ids[normalize_for_matching(item.claim)].append(item.id)

    core_ids = [
        skill_to_ids[normalize_for_matching(skill)][0]
        for skill in core_skills
        if skill_to_ids.get(normalize_for_matching(skill))
    ]

    bullets = [
        BulletCandidate(
            evidence_ids=core_ids,
            text=f"Core stack: {', '.join(_display_skill(skill) for skill in core_skills)}.",
            variant="balanced",
            provenance_notes="Skills aligned to target job",
        )
    ]

    ai_skills = [
        skill for skill in core_skills
        if normalize_for_matching(skill) in normalize_for_matching(
            "llm claude openai gemini vertex ai langgraph langchain tool use agent workflows"
        )
    ]
    if ai_skills and len(ai_skills) != len(core_skills):
        ai_ids = [
            skill_to_ids[normalize_for_matching(skill)][0]
            for skill in ai_skills
            if skill_to_ids.get(normalize_for_matching(skill))
        ]
        bullets.append(
            BulletCandidate(
                evidence_ids=ai_ids or core_ids,
                text=f"AI and workflow tooling: {', '.join(_display_skill(skill) for skill in ai_skills)}.",
                variant="balanced",
                provenance_notes="AI-specific skill alignment",
            )
        )

    return ResumeSection(
        heading="Skills Alignment",
        bullets=_unique_bullets(bullets, 2),
        order=2,
    )


def _build_education_section(
    profile: CandidateProfile | None,
    evidence: list[EvidenceItem],
) -> ResumeSection | None:
    profile = profile or CandidateProfile()
    if not profile.education and not profile.certifications:
        return None

    claim_to_id = {
        normalize_for_matching(item.claim): item.id
        for item in evidence
        if item.category in {"education", "certification"}
    }

    bullets: list[BulletCandidate] = []
    for item in profile.education[:2]:
        bullets.append(
            BulletCandidate(
                evidence_ids=[item.id],
                text=item.claim.rstrip(".") + ".",
                variant="balanced",
                provenance_notes="Education evidence",
            )
        )

    for certification in profile.certifications[:2]:
        evidence_id = claim_to_id.get(normalize_for_matching(certification))
        bullets.append(
            BulletCandidate(
                evidence_ids=[evidence_id] if evidence_id else [],
                text=certification.rstrip(".") + ".",
                variant="balanced",
                provenance_notes="Certification evidence",
            )
        )

    return ResumeSection(
        heading="Education & Certifications",
        bullets=_unique_bullets(bullets, 3),
        order=3,
    )


async def run_resume_assembler(state: WorkflowState) -> dict:
    """Assemble a resume draft from grounded bullets and candidate/profile context."""
    print("[resume_assembler] Processing...")

    profile: CandidateProfile | None = state.get("candidate_profile")
    job_briefs: list[JobBrief] = state.get("job_briefs", [])
    bullet_candidates: list[BulletCandidate] = state.get("bullet_candidates", [])
    evidence: list[EvidenceItem] = state.get("evidence", [])
    errors: list[str] = list(state.get("errors", []))

    if not job_briefs:
        errors.append("resume_assembler: no job brief available")
        return {"current_stage": "resume_assembler", "errors": errors}

    brief = job_briefs[0]
    selected_bullets = _pick_requirement_bullets(bullet_candidates, brief)
    if not selected_bullets:
        errors.append("resume_assembler: no bullet candidates available for draft assembly")
        return {"current_stage": "resume_assembler", "errors": errors}

    sections: list[ResumeSection] = [
        _build_summary_section(profile, brief, evidence, selected_bullets),
        ResumeSection(heading="Selected Highlights", bullets=selected_bullets[:6], order=1),
    ]

    skills_section = _build_skills_section(profile, brief, evidence)
    if skills_section:
        sections.append(skills_section)

    education_section = _build_education_section(profile, evidence)
    if education_section:
        sections.append(education_section)

    draft = ResumeDraft(
        candidate_name=(profile.name if profile and profile.name else "Candidate"),
        target_job=f"{brief.job_title} @ {brief.company}",
        sections=sections,
    )

    return {
        "draft": draft,
        "current_stage": "resume_assembler",
        "errors": errors,
    }
