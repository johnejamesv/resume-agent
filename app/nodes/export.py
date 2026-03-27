from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.schemas import RunArtifact
from app.services.rendering import render_markdown, render_plaintext

if TYPE_CHECKING:
    from app.graph import WorkflowState


async def run_export(state: WorkflowState) -> dict:
    """Export the final draft as markdown, plain text, and structured JSON."""
    print("[export] Processing...")

    draft = state.get("draft")
    review_findings = state.get("review_findings", [])
    decisions = state.get("arbitration_decisions", [])
    sources = state.get("sources", [])
    job_briefs = state.get("job_briefs", [])

    artifact = RunArtifact(
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        input_sources=[source.filename or source.id for source in sources],
        target_jobs=[brief.job_title for brief in job_briefs],
        final_draft=draft,
        all_findings=review_findings,
        metadata={
            "coverage_maps": [
                coverage.model_dump(mode="json")
                for coverage in state.get("coverage_maps", [])
            ],
            "gaps": [gap.model_dump(mode="json") for gap in state.get("gaps", [])],
            "arbitration_decisions": [
                decision.model_dump(mode="json") for decision in decisions
            ],
            "errors": list(state.get("errors", [])),
        },
    )

    export_outputs: dict[str, str] = {
        "json": json.dumps(
            {
                "run_artifact": artifact.model_dump(mode="json"),
                "candidate_profile": (
                    state.get("candidate_profile").model_dump(mode="json")
                    if state.get("candidate_profile") is not None
                    else None
                ),
                "job_briefs": [brief.model_dump(mode="json") for brief in job_briefs],
            },
            indent=2,
            ensure_ascii=False,
        )
    }

    if draft is not None:
        export_outputs["markdown"] = render_markdown(draft)
        export_outputs["text"] = render_plaintext(draft)
    else:
        export_outputs["markdown"] = "# No draft produced\n"
        export_outputs["text"] = "NO DRAFT PRODUCED\n"

    return {"current_stage": "export", "export_outputs": export_outputs}
