from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.review import ArbitrationDecision, ReviewFinding

if TYPE_CHECKING:
    from app.graph import WorkflowState


def _tighten_bullet_text(text: str) -> str:
    replacements = {
        "helped": "supported",
        "Helped": "Supported",
        "assisted": "supported",
        "Assisted": "Supported",
        "worked on": "built",
        "Worked on": "Built",
        "responsible for": "owned",
        "Responsible for": "Owned",
        "involved in": "contributed to",
        "Involved in": "Contributed to",
    }
    revised = text
    for old, new in replacements.items():
        revised = revised.replace(old, new)

    words = revised.split()
    if len(words) > 30:
        revised = " ".join(words[:30]).rstrip(",.") + "."
    if not revised.endswith("."):
        revised += "."
    return revised


async def run_arbiter(state: WorkflowState) -> dict:
    """Convert reviewer findings into concrete draft actions."""
    print("[arbiter] Processing...")

    draft = state.get("draft")
    findings: list[ReviewFinding] = list(state.get("review_findings", []))
    if draft is None:
        return {"current_stage": "arbiter", "arbitration_decisions": []}

    decisions: list[ArbitrationDecision] = []
    bullet_map = {
        bullet.id: bullet
        for section in draft.sections
        for bullet in section.bullets
    }
    remove_bullet_ids: set[str] = set()
    revised_text_by_id: dict[str, str] = {}

    for finding in findings:
        action = "accept"
        rationale = "No change required."
        revised_text = None

        if finding.severity == "hard_fail":
            action = "flag_for_user"
            rationale = "Removed from the exported draft until the claim can be confirmed."
            if finding.target_section in bullet_map:
                remove_bullet_ids.add(finding.target_section)
        elif finding.severity == "soft_suggestion":
            if finding.target_section in bullet_map and finding.issue_type in {
                "vague_language",
                "too_long",
                "duplicate_bullet",
            }:
                action = "revise"
                original_text = bullet_map[finding.target_section].text
                revised_text = _tighten_bullet_text(original_text)
                revised_text_by_id[finding.target_section] = revised_text
                rationale = "Applied a safe wording cleanup automatically."
            else:
                action = "flag_for_user"
                rationale = "Kept the draft but surfaced a follow-up decision for the user."

        decisions.append(
            ArbitrationDecision(
                finding_id=finding.id,
                action=action,  # type: ignore[arg-type]
                rationale=rationale,
                revised_text=revised_text,
            )
        )

    updated_sections = []
    for section in draft.sections:
        updated_bullets = []
        for bullet in section.bullets:
            if bullet.id in remove_bullet_ids:
                continue
            if bullet.id in revised_text_by_id:
                bullet = bullet.model_copy(update={"text": revised_text_by_id[bullet.id]})
            updated_bullets.append(bullet)

        if updated_bullets:
            updated_sections.append(section.model_copy(update={"bullets": updated_bullets}))

    updated_draft = draft.model_copy(
        update={
            "sections": updated_sections,
            "review_findings": findings,
            "arbitration_decisions": decisions,
        }
    )

    return {
        "current_stage": "arbiter",
        "draft": updated_draft,
        "arbitration_decisions": decisions,
    }
