from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.job import CoverageMap, JobBrief
from app.schemas.review import ReviewFinding
from app.services.deterministic import extract_metric_tokens, normalize_for_matching

if TYPE_CHECKING:
    from app.graph import WorkflowState


async def run_hiring_manager_review(state: WorkflowState) -> dict:
    """Review the draft from a fast recruiter and hiring-manager scan perspective."""
    print("[hiring_manager_review] Processing...")

    draft = state.get("draft")
    review_findings: list[ReviewFinding] = list(state.get("review_findings", []))
    job_briefs: list[JobBrief] = state.get("job_briefs", [])
    coverage_maps: list[CoverageMap] = state.get("coverage_maps", [])

    if draft is None or not job_briefs:
        return {"current_stage": "hiring_manager_review", "review_findings": review_findings}

    brief = job_briefs[0]
    coverage = coverage_maps[0] if coverage_maps else None
    sections = {normalize_for_matching(section.heading): section for section in draft.sections}
    summary_section = sections.get(normalize_for_matching("Professional Summary"))
    all_bullets = [bullet for section in draft.sections for bullet in section.bullets]
    draft_text = " ".join(bullet.text for bullet in all_bullets)

    if summary_section is None or len(summary_section.bullets) < 2:
        review_findings.append(
            ReviewFinding(
                reviewer_type="hiring_manager",
                severity="soft_suggestion",
                target_section="Professional Summary",
                issue_type="summary_weak",
                finding="Summary section is too thin to frame the candidate quickly.",
                suggested_action="Lead with two sharp bullets that position the candidate for the target role.",
            )
        )

    if not any(extract_metric_tokens(bullet.text) for bullet in all_bullets):
        review_findings.append(
            ReviewFinding(
                reviewer_type="hiring_manager",
                severity="soft_suggestion",
                target_section="Selected Highlights",
                issue_type="impact_gap",
                finding="Draft is light on quantified impact.",
                suggested_action="Prioritize bullets with scale, savings, throughput, or time reduction.",
            )
        )

    matched_keywords = [
        keyword for keyword in brief.keywords[:8]
        if normalize_for_matching(keyword) in normalize_for_matching(draft_text)
    ]
    if len(matched_keywords) < min(3, len(brief.keywords[:5])):
        review_findings.append(
            ReviewFinding(
                reviewer_type="hiring_manager",
                severity="soft_suggestion",
                target_section="Skills Alignment",
                issue_type="keyword_gap",
                finding="Draft could mirror the target job language more explicitly.",
                suggested_action="Bring more exact job keywords into summary or skills lines when evidence supports them.",
            )
        )

    if coverage is not None:
        entries_by_requirement = {entry.requirement_id: entry for entry in coverage.entries}
        for requirement in brief.must_have:
            entry = entries_by_requirement.get(requirement.id)
            if entry is None or entry.strength == "missing":
                review_findings.append(
                    ReviewFinding(
                        reviewer_type="hiring_manager",
                        severity="soft_suggestion",
                        target_section=requirement.id,
                        issue_type="coverage_gap",
                        finding=f"Must-have requirement is not represented clearly: {requirement.text}",
                        suggested_action="Either add defensible evidence for this requirement or accept that it is a real gap.",
                    )
                )

    return {"current_stage": "hiring_manager_review", "review_findings": review_findings}
