from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import StateGraph

from app.schemas.candidate import CandidateProfile, GapQuestion
from app.schemas.evidence import EvidenceItem, SourceDocument
from app.schemas.job import CoverageMap, JobBrief
from app.schemas.resume import BulletCandidate, ResumeDraft
from app.schemas.review import ArbitrationDecision, ReviewFinding

from app.nodes.ingest import run_ingest
from app.nodes.normalize_evidence import run_normalize_evidence
from app.nodes.gap_finder import run_gap_finder
from app.nodes.job_parser import run_job_parser
from app.nodes.evidence_matcher import run_evidence_matcher
from app.nodes.bullet_writer import run_bullet_writer
from app.nodes.resume_assembler import run_resume_assembler
from app.nodes.red_team_review import run_red_team_review
from app.nodes.hiring_manager_review import run_hiring_manager_review
from app.nodes.arbiter import run_arbiter
from app.nodes.export import run_export


class WorkflowState(TypedDict, total=False):
    """Full state object passed through the resume-builder pipeline."""

    sources: list[SourceDocument]
    evidence: list[EvidenceItem]
    gaps: list[GapQuestion]
    candidate_profile: CandidateProfile | None
    job_briefs: list[JobBrief]
    coverage_maps: list[CoverageMap]
    bullet_candidates: list[BulletCandidate]
    draft: ResumeDraft | None
    review_findings: list[ReviewFinding]
    arbitration_decisions: list[ArbitrationDecision]
    export_outputs: dict[str, str]  # format -> content
    current_stage: str
    errors: list[str]


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

PIPELINE_NODES: list[tuple[str, Callable]] = [
    ("ingest", run_ingest),
    ("normalize_evidence", run_normalize_evidence),
    ("gap_finder", run_gap_finder),
    ("job_parser", run_job_parser),
    ("evidence_matcher", run_evidence_matcher),
    ("bullet_writer", run_bullet_writer),
    ("resume_assembler", run_resume_assembler),
    ("red_team_review", run_red_team_review),
    ("hiring_manager_review", run_hiring_manager_review),
    ("arbiter", run_arbiter),
    ("export", run_export),
]


def build_graph():
    """Construct and compile the resume-builder LangGraph pipeline."""
    graph = StateGraph(WorkflowState)

    for name, fn in PIPELINE_NODES:
        graph.add_node(name, fn)

    for i in range(len(PIPELINE_NODES) - 1):
        graph.add_edge(PIPELINE_NODES[i][0], PIPELINE_NODES[i + 1][0])

    graph.set_entry_point("ingest")
    return graph.compile()


async def run_pipeline(
    sources: list[SourceDocument],
    job_texts: list[str],
) -> WorkflowState:
    """Build initial state, invoke the compiled graph, and return final state."""
    compiled = build_graph()

    initial_state: WorkflowState = {
        "sources": list(sources),
        "evidence": [],
        "gaps": [],
        "candidate_profile": None,
        "job_briefs": [],
        "coverage_maps": [],
        "bullet_candidates": [],
        "draft": None,
        "review_findings": [],
        "arbitration_decisions": [],
        "export_outputs": {},
        "current_stage": "init",
        "errors": [],
    }

    # Attach raw job description texts as source documents for downstream parsing
    for idx, text in enumerate(job_texts):
        initial_state["sources"].append(
            SourceDocument(
                content=text,
                source_type="other",
                filename=f"job_description_{idx + 1}.txt",
            )
        )

    result = await compiled.ainvoke(initial_state)
    return result
