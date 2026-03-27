from __future__ import annotations

from pathlib import Path

import pytest

import app.config as config_module
from app.main import _build_source
from app.graph import run_pipeline


@pytest.fixture(autouse=True)
def disable_llm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DISABLE_LLM", "1")
    config_module._singleton = None
    yield
    config_module._singleton = None


def _sample_sources() -> list:
    return [
        _build_source("sample_data/candidate_pack_1/resume.md"),
        _build_source("sample_data/candidate_pack_1/experience_notes.md"),
    ]


def _read_job(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_gen_ai_pipeline_surfaces_real_gaps():
    result = await run_pipeline(
        sources=_sample_sources(),
        job_texts=[_read_job("sample_data/jobs/sample_gen_ai_engineer.md")],
    )

    assert result["draft"] is not None
    assert "markdown" in result["export_outputs"]
    assert "json" in result["export_outputs"]
    assert result["errors"] == []

    brief = result["job_briefs"][0]
    coverage = result["coverage_maps"][0]
    requirements = {item.id: item.text for item in brief.must_have + brief.preferred}
    strengths = {requirements[item.requirement_id]: item.strength for item in coverage.entries}

    assert strengths[
        "Experience with RAG architectures: vector databases, embedding models, chunking strategies"
    ] == "missing"
    assert strengths[
        "Experience with LLM orchestration frameworks (LangChain, LangGraph, or similar)"
    ] == "missing"
    assert strengths[
        "Experience with observability tools for LLM applications (LangSmith, Langfuse)"
    ] == "missing"


@pytest.mark.asyncio
async def test_applied_ai_pipeline_highlights_domain_fit():
    result = await run_pipeline(
        sources=_sample_sources(),
        job_texts=[_read_job("sample_data/jobs/sample_applied_ai_engineer.md")],
    )

    brief = result["job_briefs"][0]
    coverage = result["coverage_maps"][0]
    requirements = {item.id: item.text for item in brief.must_have + brief.preferred}
    strengths = {requirements[item.requirement_id]: item.strength for item in coverage.entries}

    assert strengths[
        "Experience building data pipelines that process sensor, telemetry, or geospatial data"
    ] == "strong"
    assert strengths[
        "Familiarity with cloud infrastructure (GCP, AWS, or Azure) and containerized deployments"
    ] == "strong"
    assert "SpotCheck" in result["export_outputs"]["markdown"]
