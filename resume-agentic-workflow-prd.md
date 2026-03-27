# PRD: Evidence-Grounded Agentic Resume Builder

## 1. Overview

### Product name
**Resume Agentic Workflow**

### One-line summary
An evidence-grounded, multi-stage resume builder that ingests messy candidate inputs, tailors resumes to target jobs, and runs adversarial review before export.

### Dual purpose
This project has two goals:

1. **Practical utility**: help the user improve and tailor their resume for real job applications.
2. **Portfolio value**: demonstrate the design and implementation of a disciplined agentic workflow suitable for showcasing on GitHub.

This is not intended to be a generic “AI writes your resume” toy. The core value is the workflow: evidence extraction, job alignment, structured drafting, and skeptical review.

---

## 2. Problem Statement

Most AI resume tools fail in one or more of these ways:

- They write from vague conversation context instead of verified evidence.
- They produce generic bullets with weak differentiation.
- They overstate impact or invent metrics.
- They do not tailor output tightly to the job description.
- They do not expose a credible workflow that could stand as an engineering portfolio artifact.

Users need a system that can take unstructured source material—chat transcripts, old resumes, brag docs, LinkedIn content, performance notes, project summaries—and turn it into tailored, defensible resume variants.

---

## 3. Product Goals

### Primary goals
- Create a **source-grounded candidate profile** from messy inputs.
- Produce **tailored resumes** for one or more target job descriptions.
- Ensure every strong claim can be traced back to supporting evidence.
- Run **adversarial review** to catch weak, inflated, or unsupported bullets.
- Generate artifacts and traces that make the system credible as a GitHub portfolio project.

### Secondary goals
- Support iterative refinement through follow-up questions for missing data.
- Provide evaluable outputs and sample datasets for local/demo runs.
- Make the system legible to reviewers through diagrams, schemas, traces, and tests.

---

## 4. Non-Goals

- Fully autonomous job search or application submission.
- LinkedIn automation or mass application workflows.
- Resume design-heavy formatting as a primary feature.
- Support for every resume/CV subtype on day one (e.g. federal resumes, academic CVs, executive bios).
- Replacing human judgment on sensitive claims or inferred metrics.

---

## 5. Target Users

### Primary user
A technically literate job seeker who wants:
- a better resume,
- per-job tailoring,
- a visible example of agent/workflow design on GitHub.

### Secondary user
A recruiter, hiring manager, or engineer reviewing the GitHub repository as evidence of product and systems thinking.

---

## 6. User Jobs To Be Done

### Functional jobs
- Upload or paste career evidence from multiple messy sources.
- Provide one or more target job descriptions.
- Receive a tailored resume draft grounded in actual evidence.
- See what requirements are covered well vs poorly.
- Review flagged weak claims before export.

### Emotional jobs
- Feel confident the resume is truthful and defensible.
- Avoid embarrassment from inflated or fabricated claims.
- Present a polished portfolio project that signals sound architectural judgment.

---

## 7. Product Principles

1. **Evidence before prose**  
   The system should extract and structure facts before writing bullets.

2. **Deterministic shell, agentic interior**  
   The overall workflow should be graph-based and explicit, with bounded agentic nodes inside it.

3. **Reviewers can reject**  
   Review nodes should not merely “improve” copy. They should be able to fail or block unsupported content.

4. **Provenance is mandatory**  
   Strong claims should link back to source evidence.

5. **Human approval for sensitive leaps**  
   The user should explicitly approve speculative framing, inferred metrics, or major rewrites.

6. **Portfolio readability matters**  
   The repo must clearly communicate architecture, workflow, and evaluation strategy.

---

## 8. Core User Flow

1. User provides source material:
   - chat transcripts,
   - old resumes,
   - LinkedIn/About text,
   - brag docs,
   - project summaries,
   - notes,
   - performance review snippets.

2. User provides one or more target jobs.

3. System extracts and normalizes evidence into structured objects.

4. System identifies missing data and asks targeted follow-up questions.

5. System parses job requirements and optionally researches role/company terminology.

6. System maps candidate evidence to job requirements.

7. System generates bullet candidates and assembles a tailored draft.

8. System runs review passes:
   - factual review,
   - adversarial review,
   - hiring-manager review.

9. System arbitrates conflicts and prepares a revised draft.

10. User approves flagged items.

11. System exports final outputs.

---

## 9. Proposed Workflow Graph

```text
ingest
  -> normalize_evidence
  -> gap_finder
  -> job_parser
  -> optional_research
  -> evidence_matcher
  -> bullet_writer
  -> resume_assembler
  -> red_team_review
  -> hiring_manager_review
  -> arbiter
  -> human_approval
  -> export
```

### Why this structure
- The graph is explicit and easy to explain in a README.
- Most steps are bounded and deterministic.
- Agentic behavior is concentrated where it adds value:
  - research,
  - drafting,
  - adversarial review,
  - managerial review.

---

## 10. Functional Requirements

### 10.1 Ingestion
The system must accept:
- freeform pasted text,
- markdown files,
- plain text files,
- job descriptions,
- optional structured metadata.

### 10.2 Evidence Extraction
The system must extract:
- role/company/title,
- date ranges,
- project names,
- responsibilities,
- technologies/tools,
- team/stakeholder context,
- metrics and outcomes,
- leadership/scope indicators,
- source snippet provenance.

### 10.3 Candidate Profile
The system must create a canonical candidate profile with:
- work history,
- achievements,
- skills,
- education,
- certifications,
- project evidence,
- unresolved gaps.

### 10.4 Gap Finding
The system should generate targeted follow-up questions when critical information is missing, especially:
- metrics,
- dates,
- team size,
- customer/business impact,
- ownership level,
- technical scope.

### 10.5 Job Parsing
The system must parse target roles into:
- must-have requirements,
- preferred requirements,
- skills/keywords,
- domain language,
- seniority signals,
- business outcomes,
- role focus.

### 10.6 Optional Research
The system may perform bounded external research for:
- company language,
- role-specific terminology,
- industry keywords,
- relevant resume conventions.

This node must remain constrained and not own the whole workflow.

### 10.7 Evidence Matching
The system must map extracted evidence to job requirements and produce a coverage artifact showing:
- strong matches,
- weak matches,
- missing requirements,
- possible adjacent evidence.

### 10.8 Bullet Writing
The system must generate bullets from evidence, not directly from the raw prompt.

Each bullet should attempt to express:
- action,
- scope,
- method/tool,
- measurable result where available.

The system should generate multiple bullet variants where useful:
- metric-forward,
- technical-depth,
- leadership-forward,
- business-impact.

### 10.9 Resume Assembly
The system must support:
- a canonical master resume,
- a role-level base resume,
- a specific job-tailored resume.

### 10.10 Review Nodes
The system must include at minimum:

#### Factual / provenance review
Checks whether claims are supported by extracted evidence.

#### Adversarial review
Attempts to break the draft by flagging:
- unsupported claims,
- inflated metrics,
- vague language,
- misleading verbs,
- ATS keyword gaps,
- brittle interview claims,
- inconsistent dates/titles,
- privacy leaks.

#### Hiring-manager review
Assesses whether the draft is compelling in a fast human scan:
- clear strengths,
- level/seniority clarity,
- role fit,
- distinctiveness.

### 10.11 Arbitration
The system must reconcile reviewer outputs and produce:
- hard failures,
- soft suggestions,
- user-confirmation items.

### 10.12 Export
The system should export:
- markdown draft,
- structured JSON artifacts,
- optional plain text or PDF/doc outputs later.

---

## 11. Non-Functional Requirements

### Explainability
The system should expose how each bullet was derived.

### Reliability
The system should minimize unsupported or inflated statements.

### Maintainability
Workflow nodes, schemas, and services should be clearly separated.

### Observability
Runs should produce logs, traces, and inspectable intermediate artifacts.

### Reproducibility
Sample data and eval cases should allow consistent local/demo runs.

---

## 12. Data Model / State Objects

Initial schema set:

- `CandidateProfile`
- `EvidenceItem`
- `SourceDocument`
- `GapQuestion`
- `JobBrief`
- `RequirementItem`
- `CoverageMap`
- `BulletCandidate`
- `ResumeDraft`
- `ReviewFinding`
- `ArbitrationDecision`
- `RunArtifact`

### Example expectations

#### EvidenceItem
Should include:
- id,
- source_id,
- source_excerpt,
- category,
- claim,
- date context,
- entities,
- confidence,
- provenance metadata.

#### JobBrief
Should include:
- job_title,
- company,
- seniority,
- must_have_requirements,
- preferred_requirements,
- keywords,
- themes,
- domain context.

#### ReviewFinding
Should include:
- reviewer_type,
- severity,
- target_section,
- issue_type,
- finding,
- suggested_action,
- provenance reference if applicable.

---

## 13. Success Metrics

### Product-output metrics
- % of final bullets with attached provenance
- % of must-have requirements covered by at least one evidence-backed bullet
- # of unsupported claims flagged before export
- average number of weak/vague bullets remaining after review
- user-rated usefulness of final tailored resume

### Portfolio/demo metrics
- time to first successful demo run
- number of working sample runs included in repo
- quality of README and architecture clarity
- presence of evals and trace artifacts
- ability for a reviewer to understand the workflow in under 2 minutes

---

## 14. Evaluation Strategy

The repo should include offline evaluation, not just live demos.

### Must-have eval categories
1. **Evidence grounding**
   - Unsupported bullets should be flagged.
   - Unsupported metrics should not survive to final draft.

2. **Requirement coverage**
   - Must-have job requirements should be reflected when evidence exists.
   - Missing evidence should be surfaced, not hallucinated.

3. **Writing quality**
   - Bullets should be concise and action-oriented.
   - Generic filler should be reduced after review.

4. **Review strength**
   - Adversarial reviewer should catch deliberately injected weak claims.
   - Hiring-manager reviewer should distinguish sharp vs muddy summaries.

5. **Workflow integrity**
   - State should pass cleanly across nodes.
   - Failure states should be inspectable.

### Example eval cases
- Injected fake metric: “increased revenue by 35%” without evidence
- Weak bullet: “helped with migration work”
- Missing keyword coverage for a target role
- Conflicting dates in source materials
- Resume claim that sounds good but is vulnerable in interview probing

---

## 15. Technical Architecture

### Recommended stack
- **Language**: Python
- **Workflow orchestration**: LangGraph
- **Model/tool layer**: OpenAI Responses API
- **Schemas**: Pydantic
- **API surface**: FastAPI
- **Persistence**: SQLite or Postgres
- **Frontend**: optional minimal UI later
- **Observability**: traces/logs, optional LangSmith or equivalent

### Architectural stance
Use a graph workflow, not a free-roaming autonomous agent.

The outer structure should remain explicit and controlled. Agentic behavior should be used where reasoning, drafting, or critique materially benefits from it.

---

## 16. Repository Structure (Initial Proposal)

```text
resume-agentic-workflow/
├─ README.md
├─ pyproject.toml
├─ app/
│  ├─ main.py
│  ├─ graph.py
│  ├─ config.py
│  ├─ nodes/
│  │  ├─ ingest.py
│  │  ├─ normalize_evidence.py
│  │  ├─ gap_finder.py
│  │  ├─ job_parser.py
│  │  ├─ optional_research.py
│  │  ├─ evidence_matcher.py
│  │  ├─ bullet_writer.py
│  │  ├─ resume_assembler.py
│  │  ├─ red_team_review.py
│  │  ├─ hiring_manager_review.py
│  │  ├─ arbiter.py
│  │  └─ export.py
│  ├─ schemas/
│  │  ├─ candidate.py
│  │  ├─ evidence.py
│  │  ├─ job.py
│  │  ├─ review.py
│  │  └─ resume.py
│  └─ services/
│     ├─ llm.py
│     ├─ parsing.py
│     ├─ scoring.py
│     └─ rendering.py
├─ sample_data/
│  ├─ candidate_pack_1/
│  ├─ candidate_pack_2/
│  └─ jobs/
├─ evals/
│  ├─ cases/
│  └─ runners/
├─ tests/
└─ docs/
   ├─ architecture.md
   └─ traces/
```

---

## 17. MVP Scope

### Include in MVP
- Single-candidate workflow
- 1–3 target job descriptions
- Evidence extraction from pasted text / markdown
- Canonical profile generation
- Job parsing
- Evidence matching
- Resume bullet generation
- Resume assembly in markdown
- Adversarial review
- Hiring-manager review
- Final markdown export
- README, diagrams, schemas, sample data, evals

### Exclude from MVP
- Full web UI
- Google Drive / external source ingestion
- DOCX/PDF-perfect export
- Multi-user auth
- Full portfolio site
- Broad template/theme system

---

## 18. Risks and Mitigations

### Risk: hallucinated or inflated claims
**Mitigation**: provenance requirements, adversarial review, user approval for sensitive claims.

### Risk: generic outputs
**Mitigation**: strong evidence mapping, job-specific requirement coverage, multiple bullet variants, hiring-manager review.

### Risk: architecture looks gimmicky on GitHub
**Mitigation**: keep graph explicit, document why each node exists, include evals and traces.

### Risk: too much complexity for MVP
**Mitigation**: build the graph and schemas first; keep research and export layers narrow.

### Risk: weak sample data makes the demo unconvincing
**Mitigation**: curate 2–3 realistic sample candidate packs and job descriptions.

---

## 19. Milestones

### Milestone 1: Project bootstrap
- repo scaffold
- README skeleton
- schemas
- graph skeleton
- sample data placeholders

### Milestone 2: Core pipeline
- ingest
- normalize evidence
- job parser
- matcher
- bullet writer
- assembler

### Milestone 3: Review layer
- red-team review
- hiring-manager review
- arbiter
- user confirmation rules

### Milestone 4: Evaluation and polish
- eval cases
- trace examples
- architecture docs
- portfolio-ready README

---

## 20. Open Questions

- Should the first export target be markdown only, or markdown + plain text?
- How much role/company research is worth including in MVP?
- Should the arbiter be rule-based, model-based, or hybrid?
- How aggressively should the system infer metrics from soft evidence?
- What threshold triggers mandatory human approval?

---

## 21. Launch Criteria

The MVP is “launchable” when:

- A user can provide messy candidate context and at least one job description.
- The system produces a tailored markdown resume.
- Every strong bullet is traceable to extracted evidence or explicitly flagged for confirmation.
- The adversarial reviewer reliably catches at least the obvious injected weak/fake claims in sample evals.
- The GitHub repo clearly demonstrates architecture, workflow, and evaluation.

---

## 22. Final Positioning

This project should present as:

> A disciplined agentic workflow for evidence-grounded resume tailoring, with explicit state, bounded research, adversarial review, and evaluation artifacts.

That positioning is stronger than “AI resume builder” and stronger than “multi-agent demo.” It signals product judgment, systems design, and practical restraint.
