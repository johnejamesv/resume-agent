from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.schemas.review import ReviewFinding
from app.services.deterministic import extract_metric_tokens, normalize_for_matching
from app.services.llm import llm_available

if TYPE_CHECKING:
    from app.graph import WorkflowState


class _AdversarialFinding(BaseModel):
    severity: str = Field(description="hard_fail | soft_suggestion | info")
    target_section: str | None = Field(description="Bullet id this finding targets")
    issue_type: str = Field(
        description=(
            "One of: unsupported_claim, inflated_metric, vague_language, "
            "misleading_verb, brittle_interview_claim, inconsistency, privacy_leak"
        )
    )
    finding: str = Field(description="What the problem is, in one sentence")
    suggested_action: str | None = Field(description="How to fix it")


class _AdversarialFindings(BaseModel):
    findings: list[_AdversarialFinding]


SYSTEM_PROMPT = (
    "You are a skeptical resume reviewer. Your job is to find problems. "
    "Flag: unsupported claims (no evidence backing), inflated or unverifiable "
    "metrics, vague filler language ('helped with', 'assisted in', 'worked on'), "
    "misleading action verbs, claims that would crumble under interview probing, "
    "inconsistent dates or titles. Be ruthless but fair."
)

VAGUE_PATTERNS = (
    "helped",
    "assisted",
    "worked on",
    "responsible for",
    "involved in",
)


def _normalize_metric(token: str) -> str:
    return re.sub(r"[,\s]", "", token.lower())


def _serialize_bullets(draft) -> str:
    lines: list[str] = []
    for section in draft.sections:
        for bullet in section.bullets:
            lines.append(
                f"- [{bullet.id}] \"{bullet.text}\" "
                f"(evidence: {bullet.evidence_ids or 'NONE'}, "
                f"provenance: {bullet.provenance_notes or 'NONE'})"
            )
    return "\n".join(lines) or "(no bullets)"


def _serialize_evidence(evidence: list) -> str:
    lines: list[str] = []
    for item in evidence:
        lines.append(
            f"- [{item.id}] claim=\"{item.claim}\" "
            f"excerpt=\"{item.source_excerpt[:200]}\""
        )
    return "\n".join(lines) or "(no evidence)"


def _rule_based_findings(draft, evidence: list) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    seen_text: dict[str, str] = {}
    evidence_by_id = {item.id: item for item in evidence}

    for section in draft.sections:
        for bullet in section.bullets:
            normalized_text = normalize_for_matching(bullet.text)
            if not bullet.evidence_ids:
                findings.append(
                    ReviewFinding(
                        reviewer_type="adversarial",
                        severity="hard_fail",
                        target_section=bullet.id,
                        issue_type="unsupported_claim",
                        finding="Bullet has no provenance-linked evidence.",
                        suggested_action="Remove the bullet or attach supporting evidence.",
                    )
                )

            support_text = " ".join(
                f"{evidence_by_id[evidence_id].claim} {evidence_by_id[evidence_id].source_excerpt}"
                for evidence_id in bullet.evidence_ids
                if evidence_id in evidence_by_id
            )
            supported_metrics = {_normalize_metric(token) for token in extract_metric_tokens(support_text)}
            bullet_metrics = [_normalize_metric(token) for token in extract_metric_tokens(bullet.text)]
            unsupported_metrics = [
                token for token in bullet_metrics
                if token not in supported_metrics and token not in {"1", "2", "3"}
            ]
            if unsupported_metrics:
                findings.append(
                    ReviewFinding(
                        reviewer_type="adversarial",
                        severity="hard_fail",
                        target_section=bullet.id,
                        issue_type="inflated_metric",
                        finding=f"Bullet includes unsupported numeric claim(s): {', '.join(unsupported_metrics)}.",
                        suggested_action="Use only metrics that appear in the source evidence.",
                    )
                )

            if any(pattern in bullet.text.lower() for pattern in VAGUE_PATTERNS):
                findings.append(
                    ReviewFinding(
                        reviewer_type="adversarial",
                        severity="soft_suggestion",
                        target_section=bullet.id,
                        issue_type="vague_language",
                        finding="Bullet uses vague language that weakens credibility.",
                        suggested_action="Replace filler verbs with a concrete action and outcome.",
                    )
                )

            if len(bullet.text.split()) > 32:
                findings.append(
                    ReviewFinding(
                        reviewer_type="adversarial",
                        severity="soft_suggestion",
                        target_section=bullet.id,
                        issue_type="too_long",
                        finding="Bullet is longer than a fast resume scan wants.",
                        suggested_action="Tighten the bullet to one concise sentence.",
                    )
                )

            if normalized_text in seen_text:
                findings.append(
                    ReviewFinding(
                        reviewer_type="adversarial",
                        severity="soft_suggestion",
                        target_section=bullet.id,
                        issue_type="duplicate_bullet",
                        finding="Bullet overlaps heavily with another bullet in the draft.",
                        suggested_action="Remove the duplicate or differentiate the evidence.",
                    )
                )
            else:
                seen_text[normalized_text] = bullet.id

    return findings


async def run_red_team_review(state: WorkflowState) -> dict:
    """Adversarial review that tries to break every claim in the draft."""
    from app.services.llm import complete_structured

    print("[red_team_review] Starting adversarial review...")

    draft = state.get("draft")
    if draft is None:
        print("[red_team_review] No draft - skipping.")
        return {"current_stage": "red_team_review"}

    evidence = state.get("evidence", [])
    errors = list(state.get("errors", []))
    review_findings: list[ReviewFinding] = list(state.get("review_findings", []))
    review_findings.extend(_rule_based_findings(draft, evidence))

    if llm_available():
        bullets_text = _serialize_bullets(draft)
        evidence_text = _serialize_evidence(evidence)
        user_prompt = (
            "Review these resume bullets for problems. Cross-reference each "
            "bullet against the evidence list. A bullet with no matching "
            "evidence_id or whose claim goes beyond the evidence is unsupported.\n\n"
            "## Bullets\n" + bullets_text + "\n\n"
            "## Available Evidence\n" + evidence_text + "\n\n"
            "Return ALL findings. For each, include severity (hard_fail for "
            "unsupported claims or inflated metrics, soft_suggestion for vague "
            "language or style issues, info for minor notes), the bullet id "
            "as target_section, the issue_type, a one-sentence finding, and "
            "a suggested_action."
        )

        try:
            result = await complete_structured(
                user_prompt,
                response_model=_AdversarialFindings,
                system=SYSTEM_PROMPT,
                temperature=0.3,
            )
            existing_keys = {
                (finding.target_section, finding.issue_type, finding.finding)
                for finding in review_findings
            }
            for item in result.findings:
                finding = ReviewFinding(
                    reviewer_type="adversarial",
                    severity=item.severity if item.severity in ("hard_fail", "soft_suggestion", "info") else "info",
                    target_section=item.target_section,
                    issue_type=item.issue_type,
                    finding=item.finding,
                    suggested_action=item.suggested_action,
                )
                key = (finding.target_section, finding.issue_type, finding.finding)
                if key not in existing_keys:
                    review_findings.append(finding)
                    existing_keys.add(key)
        except Exception as exc:
            msg = f"[red_team_review] LLM call failed: {exc}"
            print(msg)
            errors.append(msg)

    counts = {"hard_fail": 0, "soft_suggestion": 0, "info": 0}
    for finding in review_findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    print(
        f"[red_team_review] {len(review_findings)} findings - "
        f"{counts['hard_fail']} hard_fail, {counts['soft_suggestion']} soft, "
        f"{counts['info']} info"
    )

    return {
        "review_findings": review_findings,
        "current_stage": "red_team_review",
        "errors": errors,
    }
