# Resume Agentic Workflow

An evidence-grounded, multi-stage resume builder that ingests messy candidate inputs, tailors resumes to target jobs, and runs adversarial review before export.

## Why This Exists

Most AI resume tools fail because they write from vague context instead of verified evidence, produce generic bullets, overstate impact, and don't tailor tightly to the job description. This project takes a different approach:

1. **Extract evidence first** — structure facts from messy sources before writing prose
2. **Map evidence to requirements** — explicit coverage analysis against target JDs
3. **Generate grounded bullets** — every strong claim traces back to source material
4. **Adversarial review** — a red-team pass flags unsupported claims, inflated metrics, and vague language before a human ever sees the output

## Architecture

```
Deterministic shell, agentic interior
```

The outer workflow is an explicit LangGraph pipeline — no free-roaming autonomous agents. Agentic behavior (LLM calls for drafting, critique, research) is concentrated inside bounded nodes where it adds value.

```
ingest → normalize_evidence → gap_finder → job_parser → evidence_matcher
    → bullet_writer → resume_assembler → red_team_review
    → hiring_manager_review → arbiter → export
```

### Pipeline Stages

| Stage | Purpose |
|-------|---------|
| **Ingest** | Accept resumes, transcripts, brag docs, notes, project summaries |
| **Normalize Evidence** | Extract structured evidence items with source provenance |
| **Gap Finder** | Identify missing data (metrics, dates, scope) and generate follow-up questions |
| **Job Parser** | Parse target JDs into must-have/preferred requirements with keywords |
| **Evidence Matcher** | Map candidate evidence to job requirements; produce coverage scores |
| **Bullet Writer** | Generate bullet variants (metric-forward, technical-depth, leadership, business-impact) |
| **Resume Assembler** | Build a tailored draft from matched bullets and sections |
| **Red Team Review** | Adversarial pass: flag unsupported claims, inflated metrics, vague filler |
| **Hiring Manager Review** | Assess scan-ability, level clarity, role fit, distinctiveness |
| **Arbiter** | Reconcile reviewer findings into accept/revise/flag-for-user decisions |
| **Export** | Render to markdown, plain text, and structured JSON with provenance |

## Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) (explicit state graph, not autonomous agents)
- **Models**: Model-agnostic — supports Anthropic (Claude) and OpenAI via official SDKs
- **Schemas**: Pydantic v2 (14 models across 5 domain modules)
- **API**: FastAPI (planned)
- **Language**: Python 3.11+

## Data Model

```
SourceDocument → EvidenceItem → CandidateProfile
JobBrief → RequirementItem → CoverageMap
BulletCandidate → ResumeSection → ResumeDraft
ReviewFinding → ArbitrationDecision → RunArtifact
```

Every bullet candidate carries `evidence_ids` linking back to the extracted evidence, and every evidence item carries `source_id` linking back to the original document. Provenance is not optional.

## Quickstart

```bash
# Clone and install
git clone https://github.com/johnejamesv/resume-agentic-workflow.git
cd resume-agentic-workflow
pip install -e .

# Configure API keys (optional)
cp .env.example .env
# Edit .env with your Anthropic and/or OpenAI API key
# Or set DISABLE_LLM=1 to force deterministic local mode

# Run with sample data
python -m app.main \
  --sources sample_data/candidate_pack_1/resume.md \
             sample_data/candidate_pack_1/experience_notes.md \
  --jobs sample_data/jobs/sample_gen_ai_engineer.md
```

## Project Structure

```
resume-agentic-workflow/
├── app/
│   ├── main.py              # CLI entry point
│   ├── graph.py              # LangGraph pipeline definition
│   ├── config.py             # Environment / model configuration
│   ├── nodes/                # Pipeline stage implementations
│   │   ├── ingest.py
│   │   ├── normalize_evidence.py
│   │   ├── gap_finder.py
│   │   ├── job_parser.py
│   │   ├── evidence_matcher.py
│   │   ├── bullet_writer.py
│   │   ├── resume_assembler.py
│   │   ├── red_team_review.py
│   │   ├── hiring_manager_review.py
│   │   ├── arbiter.py
│   │   └── export.py
│   ├── schemas/              # Pydantic data models
│   │   ├── evidence.py       # SourceDocument, EvidenceItem
│   │   ├── candidate.py      # CandidateProfile, GapQuestion
│   │   ├── job.py            # JobBrief, RequirementItem, CoverageMap
│   │   ├── resume.py         # BulletCandidate, ResumeDraft, RunArtifact
│   │   └── review.py         # ReviewFinding, ArbitrationDecision
│   └── services/
│       ├── llm.py            # Model-agnostic LLM abstraction (Anthropic + OpenAI)
│       ├── deterministic.py  # Deterministic fallback extraction/matching logic
│       ├── parsing.py        # Text normalization
│       └── rendering.py      # Markdown and plain text export
├── sample_data/
│   ├── candidate_pack_1/     # Sample candidate materials
│   └── jobs/                 # Sample job descriptions
├── evals/                    # Evaluation cases and runners
├── tests/
└── docs/
```

## Design Principles

1. **Evidence before prose** — extract and structure facts before writing bullets
2. **Deterministic shell, agentic interior** — the graph is explicit; LLM calls are bounded
3. **Reviewers can reject** — review nodes can fail or block content, not just improve copy
4. **Provenance is mandatory** — strong claims link back to source evidence
5. **Human approval for sensitive leaps** — speculative framing and inferred metrics require user sign-off

## Status

**Current: Core MVP pipeline is running.** The repo now supports evidence extraction, job parsing, coverage mapping, bullet generation, draft assembly, review, arbitration, and export in deterministic local mode, with optional LLM-backed upgrades when API keys are configured.

Current verification:
- `pytest` passes for both the GenAI and applied-AI sample flows
- Sample runs export markdown, plain text, and JSON artifacts
- Unsupported GenAI claims stay marked missing instead of being silently fabricated

## License

MIT
