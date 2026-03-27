from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.evidence import SourceDocument
from app.services.parsing import extract_text

if TYPE_CHECKING:
    from app.graph import WorkflowState


def _is_job_description(doc: SourceDocument) -> bool:
    """Return True if the document looks like a job description."""
    return doc.source_type == "other" and bool(
        doc.filename and "job_description" in doc.filename.lower()
    )


async def run_ingest(state: WorkflowState) -> dict:
    """Validate and clean all source documents.

    - Normalizes content via extract_text
    - Separates job descriptions from candidate sources
    - Returns cleaned sources list ready for downstream nodes
    """
    sources: list[SourceDocument] = state.get("sources", [])
    errors: list[str] = list(state.get("errors", []))

    if not sources:
        errors.append("ingest: no source documents provided")
        print("[ingest] No source documents provided")
        return {"sources": [], "errors": errors, "current_stage": "ingest"}

    cleaned: list[SourceDocument] = []
    jd_count = 0
    candidate_count = 0

    for doc in sources:
        try:
            normalized = extract_text(doc.content, doc.source_type)
            if not normalized:
                errors.append(f"ingest: empty content after cleaning '{doc.filename}'")
                continue
            updated = doc.model_copy(update={"content": normalized})
            cleaned.append(updated)

            if _is_job_description(doc):
                jd_count += 1
            else:
                candidate_count += 1
        except Exception as exc:
            errors.append(f"ingest: failed to process '{doc.filename}': {exc}")

    print(
        f"[ingest] Processed {len(cleaned)} sources "
        f"({candidate_count} candidate, {jd_count} job description)"
    )

    return {"sources": cleaned, "errors": errors, "current_stage": "ingest"}
