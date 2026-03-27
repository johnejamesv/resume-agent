from __future__ import annotations

import re
import uuid
from collections import defaultdict

from app.schemas import (
    BulletCandidate,
    CandidateProfile,
    CoverageEntry,
    CoverageMap,
    EvidenceItem,
    GapQuestion,
    JobBrief,
    RequirementItem,
)
from app.schemas.evidence import SourceDocument

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
METRIC_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?(?:\+|%|k|m|mm|x)?", re.IGNORECASE)
HEADING_SPLIT_RE = re.compile(r"\s+\|\s+")
DATE_HINT_RE = re.compile(
    r"(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b.*?\d{4}"
    r"|\b\d{4}\s*[-–]\s*(?:present|\d{4})\b|\bpresent\b)",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

STOPWORDS = {
    "a",
    "an",
    "and",
    "application",
    "applications",
    "at",
    "be",
    "build",
    "building",
    "built",
    "by",
    "experience",
    "familiarity",
    "for",
    "from",
    "framework",
    "frameworks",
    "have",
    "in",
    "into",
    "knowledge",
    "looking",
    "maintain",
    "methodologies",
    "models",
    "of",
    "on",
    "or",
    "our",
    "preferred",
    "production",
    "role",
    "skills",
    "stack",
    "systems",
    "the",
    "tool",
    "tools",
    "to",
    "understanding",
    "using",
    "with",
    "workflow",
    "workflows",
    "years",
    "you",
    "your",
}

KNOWN_TERMS = [
    "agent workflows",
    "agentic ai",
    "aws",
    "azure",
    "benchmarking",
    "chunking strategies",
    "ci cd",
    "claude",
    "claude api",
    "claude code",
    "cloud run",
    "cloud sql",
    "cloud storage",
    "computer vision",
    "docker",
    "embedding models",
    "embeddings",
    "evaluation",
    "fastapi",
    "fine tuning",
    "function calling",
    "gcp",
    "gemini",
    "geospatial",
    "github actions",
    "langchain",
    "langfuse",
    "langgraph",
    "langsmith",
    "llm",
    "llm evaluation",
    "multimodal",
    "observability",
    "openai",
    "openai api",
    "openai codex",
    "pgvector",
    "pinecone",
    "playwright",
    "postgresql",
    "prompt engineering",
    "pydantic",
    "python",
    "rag",
    "react",
    "retrieval augmented generation",
    "rlhf",
    "sensor data",
    "sql",
    "sqlalchemy",
    "streaming",
    "structured output",
    "tanstack query",
    "telemetry",
    "terraform",
    "tool use",
    "typescript",
    "vector databases",
    "vector db",
    "vercel",
    "vertex ai",
    "vite",
    "weaviate",
    "workflow orchestration",
    "zustand",
]

SPECIALIZED_TERMS = {
    "benchmarking",
    "chunking strategies",
    "embedding models",
    "evaluation",
    "fine tuning",
    "langchain",
    "langfuse",
    "langgraph",
    "langsmith",
    "open source",
    "pgvector",
    "pinecone",
    "rag",
    "retrieval augmented generation",
    "rlhf",
    "vector databases",
    "weaviate",
}

CONCEPT_ALIASES = {
    "llm": {
        "llm",
        "gpt 4",
        "openai",
        "openai api",
        "claude",
        "claude api",
        "claude code",
        "gemini",
        "vertex ai",
        "prompt engineering",
        "structured output",
    },
    "rag": {
        "rag",
        "retrieval augmented generation",
        "vector databases",
        "vector db",
        "pgvector",
        "pinecone",
        "weaviate",
        "embedding models",
        "embeddings",
        "chunking strategies",
    },
    "agents": {
        "agent workflows",
        "agentic ai",
        "tool use",
        "function calling",
        "workflow orchestration",
        "langgraph",
    },
    "cloud": {
        "gcp",
        "aws",
        "azure",
        "cloud run",
        "cloud sql",
        "cloud storage",
        "docker",
        "terraform",
        "github actions",
    },
    "frontend": {
        "react",
        "typescript",
        "vite",
        "zustand",
        "tanstack query",
    },
    "backend": {
        "python",
        "fastapi",
        "postgresql",
        "sqlalchemy",
        "sql",
        "pydantic",
    },
    "evals": {
        "evaluation",
        "benchmarking",
        "llm evaluation",
        "langsmith",
        "langfuse",
        "observability",
    },
    "multimodal": {
        "multimodal",
        "computer vision",
        "sensor data",
        "telemetry",
        "vertex ai",
        "gemini",
    },
}

STRONG_VERBS = (
    "architected",
    "automated",
    "built",
    "classified",
    "created",
    "delivered",
    "designed",
    "developed",
    "engineered",
    "executed",
    "integrated",
    "led",
    "managed",
    "optimized",
    "replaced",
    "serve",
    "served",
    "shipped",
)


def normalize_for_matching(text: str) -> str:
    cleaned = text.lower()
    cleaned = cleaned.replace("ci/cd", "ci cd")
    cleaned = cleaned.replace("llm-powered", "llm powered")
    cleaned = cleaned.replace("gpt-4", "gpt 4")
    cleaned = cleaned.replace("rag-based", "rag based")
    cleaned = re.sub(r"[^a-z0-9+]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _contains_normalized_term(normalized_text: str, term: str) -> bool:
    normalized_term = normalize_for_matching(term)
    if not normalized_term:
        return False
    haystack = f" {normalized_text} "
    needle = f" {normalized_term} "
    return needle in haystack


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_for_matching(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item.strip())
    return result


def extract_keywords(text: str) -> list[str]:
    normalized = normalize_for_matching(text)
    found: list[str] = []
    for term in KNOWN_TERMS:
        if _contains_normalized_term(normalized, term):
            found.append(term)

    tokens = [
        token
        for token in normalized.split()
        if len(token) > 2 and token not in STOPWORDS
    ]
    return dedupe_preserve_order(found + tokens[:10])


def extract_concepts(text: str) -> set[str]:
    normalized = normalize_for_matching(text)
    concepts: set[str] = set()
    for concept, aliases in CONCEPT_ALIASES.items():
        if any(_contains_normalized_term(normalized, alias) for alias in aliases):
            concepts.add(concept)
    return concepts


def extract_metric_tokens(text: str) -> list[str]:
    return METRIC_RE.findall(text)


def strip_markdown(text: str) -> str:
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
    cleaned = cleaned.replace("—", "-")
    cleaned = cleaned.replace("–", "-")
    return cleaned.strip(" -*")


def extract_header_metadata(content: str) -> dict[str, str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    name = ""
    email = ""
    location = ""

    for idx, line in enumerate(lines):
        if line.startswith("# "):
            name = strip_markdown(line[2:])
            if idx + 1 < len(lines) and EMAIL_RE.search(lines[idx + 1]):
                contact_parts = [part.strip() for part in lines[idx + 1].split("|")]
                if contact_parts:
                    location = contact_parts[0]
                match = EMAIL_RE.search(lines[idx + 1])
                if match:
                    email = match.group(0)
            break

    summary = extract_section_text(content, "PROFESSIONAL SUMMARY")

    return {
        "name": name,
        "email": email,
        "location": location,
        "summary": summary,
    }


def extract_section_text(content: str, heading: str) -> str:
    target = heading.lower()
    lines = content.splitlines()
    collecting = False
    buffer: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("## "):
            current = strip_markdown(line[3:]).lower()
            if collecting and current != target:
                break
            collecting = current == target
            continue
        if collecting and line and not re.fullmatch(r"-{3,}", line):
            buffer.append(strip_markdown(line))

    return " ".join(buffer).strip()


def _looks_like_role_heading(text: str) -> bool:
    parts = [part.strip() for part in HEADING_SPLIT_RE.split(text)]
    return len(parts) >= 2 and DATE_HINT_RE.search(text) is not None


def _heading_date_context(text: str) -> str | None:
    match = DATE_HINT_RE.search(text)
    return match.group(0) if match else None


def _classify_heading(section: str, heading: str) -> str | None:
    section_lower = section.lower()
    if "project" in section_lower:
        return "project"
    if "experience" in section_lower and _looks_like_role_heading(heading):
        return "role"
    if "education" in section_lower:
        return "education"
    return None


def _classify_claim(section: str, subheading: str, claim: str) -> str:
    section_lower = section.lower()
    subheading_lower = subheading.lower()
    claim_lower = claim.lower()

    if "technical skills" in section_lower:
        return "skill"
    if "education" in section_lower:
        if any(term in claim_lower for term in ("certificate", "certification", "course", "academy")):
            return "certification"
        return "education"
    if "project" in section_lower or "architecture" in subheading_lower:
        if any(term in claim_lower for term in ("lead", "architect", "managed", "sole engineer")):
            return "leadership"
        if extract_metric_tokens(claim_lower):
            return "metric"
        return "project"
    if "experience" in section_lower:
        if any(term in claim_lower for term in ("lead", "managed", "directed", "served", "serve as")):
            return "leadership"
        if extract_metric_tokens(claim_lower):
            return "metric"
        return "achievement"
    if "summary" in section_lower:
        if extract_metric_tokens(claim_lower):
            return "metric"
        return "achievement"
    if any(term in claim_lower for term in ("pilot certificate", "langchain academy")):
        return "certification"
    if any(term in claim_lower for term in ("engineer", "lead", "architect")) and DATE_HINT_RE.search(claim_lower):
        return "role"
    if extract_metric_tokens(claim_lower):
        return "metric"
    if extract_keywords(claim):
        return "skill"
    return "achievement"


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    if parts:
        return parts
    return [text.strip()] if text.strip() else []


def _add_evidence_item(
    items: list[EvidenceItem],
    seen: set[tuple[str, str, str]],
    source_id: str,
    source_excerpt: str,
    category: str,
    claim: str,
    *,
    date_context: str | None = None,
    metadata: dict | None = None,
) -> None:
    clean_claim = strip_markdown(claim).strip()
    if not clean_claim:
        return

    key = (source_id, category, normalize_for_matching(clean_claim))
    if key in seen:
        return
    seen.add(key)

    items.append(
        EvidenceItem(
            source_id=source_id,
            source_excerpt=source_excerpt.strip()[:400],
            category=category,
            claim=clean_claim,
            date_context=date_context,
            entities=extract_keywords(clean_claim)[:6],
            confidence=0.65 if category == "skill" else 0.8,
            metadata=metadata or {},
        )
    )


def extract_evidence_fallback(doc: SourceDocument) -> list[EvidenceItem]:
    section = ""
    subheading = ""
    items: list[EvidenceItem] = []
    seen: set[tuple[str, str, str]] = set()

    for raw_line in doc.content.splitlines():
        line = raw_line.strip()
        if not line or re.fullmatch(r"-{3,}", line):
            continue
        if line.startswith("# "):
            continue
        if EMAIL_RE.search(line):
            continue
        if line.startswith("## "):
            section = strip_markdown(line[3:])
            subheading = ""
            continue
        if line.startswith("### "):
            subheading = strip_markdown(line[4:])
            category = _classify_heading(section, subheading)
            if category:
                _add_evidence_item(
                    items,
                    seen,
                    doc.id,
                    raw_line,
                    category,
                    subheading,
                    date_context=_heading_date_context(subheading),
                    metadata={"section": section, "subheading": subheading},
                )
            continue

        if "technical skills" in section.lower() and line.startswith("- "):
            skill_line = strip_markdown(line[2:])
            group, _, remainder = skill_line.partition(":")
            skills = [
                skill.strip()
                for skill in re.split(r",|;|/", remainder or group)
                if skill.strip()
            ]
            for skill in skills:
                _add_evidence_item(
                    items,
                    seen,
                    doc.id,
                    raw_line,
                    "skill",
                    skill,
                    metadata={"section": section, "skill_group": group.strip()},
                )
            continue

        if line.startswith("- "):
            claim = strip_markdown(line[2:])
            category = _classify_claim(section, subheading, claim)
            _add_evidence_item(
                items,
                seen,
                doc.id,
                raw_line,
                category,
                claim,
                date_context=_heading_date_context(subheading),
                metadata={"section": section, "subheading": subheading},
            )
            for keyword in extract_keywords(claim):
                if keyword in {"evaluation", "benchmarking"} or keyword in KNOWN_TERMS:
                    _add_evidence_item(
                        items,
                        seen,
                        doc.id,
                        raw_line,
                        "skill",
                        keyword,
                        metadata={
                            "section": section,
                            "subheading": subheading,
                            "derived_from": claim,
                        },
                    )
            continue

        if section:
            for sentence in _split_sentences(strip_markdown(line)):
                category = _classify_claim(section, subheading, sentence)
                _add_evidence_item(
                    items,
                    seen,
                    doc.id,
                    raw_line,
                    category,
                    sentence,
                    date_context=_heading_date_context(subheading),
                    metadata={"section": section, "subheading": subheading},
                )

    return items


def build_candidate_profile(evidence: list[EvidenceItem], sources: list[SourceDocument]) -> CandidateProfile:
    profile = CandidateProfile()

    for source in sources:
        header = extract_header_metadata(source.content)
        if header["name"] and not profile.name:
            profile.name = header["name"]
        if header["email"] and not profile.email:
            profile.email = header["email"]
        if header["location"] and not profile.location:
            profile.location = header["location"]
        if header["summary"] and not profile.summary:
            profile.summary = header["summary"]

    for item in evidence:
        if item.category == "role":
            profile.work_history.append(item)
        elif item.category in {"achievement", "metric", "leadership"}:
            profile.achievements.append(item)
        elif item.category == "skill":
            profile.skills.append(item.claim)
        elif item.category == "education":
            profile.education.append(item)
        elif item.category == "certification":
            profile.certifications.append(item.claim)
        elif item.category == "project":
            profile.project_evidence.append(item)

    profile.skills = dedupe_preserve_order(profile.skills)
    profile.certifications = dedupe_preserve_order(profile.certifications)
    return profile


def build_gap_questions_fallback(
    evidence: list[EvidenceItem],
    profile: CandidateProfile | None,
) -> list[GapQuestion]:
    profile = profile or CandidateProfile()
    evidence_text = " ".join(item.claim for item in evidence).lower()
    questions: list[GapQuestion] = []

    def add(question: str, category: str, priority: str) -> None:
        questions.append(
            GapQuestion(
                id=str(uuid.uuid4()),
                question=question,
                category=category,
                priority=priority,
            )
        )

    metric_count = sum(1 for item in evidence if item.category == "metric" or extract_metric_tokens(item.claim))
    if metric_count < 3:
        add(
            "Which projects or roles have defensible metrics you can add, such as scale, throughput, savings, or time reduction?",
            "metrics",
            "critical",
        )

    dated_roles = sum(1 for item in evidence if item.category == "role" and item.date_context)
    if dated_roles == 0:
        add(
            "Can you add clearer date ranges for your core roles or projects so chronology is easy to verify?",
            "dates",
            "important",
        )

    if not any(term in evidence_text for term in ("team", "sole engineer", "led", "managed", "stakeholder", "cross-functional")):
        add(
            "What was your scope of ownership on the strongest projects: team size, decision authority, and which parts you owned directly?",
            "scope",
            "important",
        )

    if not any(term in evidence_text for term in ("saved", "reduced", "increased", "eliminated", "minutes", "days", "revenue", "cost")):
        add(
            "Which bullets can be tied to business or operational outcomes instead of just technical implementation details?",
            "impact",
            "important",
        )

    if not profile.education and not profile.certifications:
        add(
            "Should education, certifications, or domain-specific training be added to strengthen credibility for target roles?",
            "education",
            "nice_to_have",
        )

    return questions


def parse_job_brief_fallback(doc: SourceDocument) -> JobBrief:
    title = "Target Role"
    company = "Unknown Company"
    seniority = None
    current_h2 = ""
    current_h3 = ""
    must_have: list[RequirementItem] = []
    preferred: list[RequirementItem] = []
    about_lines: list[str] = []
    themes: list[str] = []
    keyword_sources: list[str] = []

    for raw_line in doc.content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            heading = strip_markdown(line[2:])
            title = heading.split(":", 1)[1].strip() if ":" in heading else heading
            continue
        if line.startswith("**Company**"):
            company = strip_markdown(line.split(":", 1)[1]) if ":" in line else company
            continue
        if line.startswith("**Level**"):
            seniority = strip_markdown(line.split(":", 1)[1]) if ":" in line else seniority
            continue
        if line.startswith("## "):
            current_h2 = strip_markdown(line[3:])
            current_h3 = ""
            continue
        if line.startswith("### "):
            current_h3 = strip_markdown(line[4:])
            continue
        if current_h2 == "About the Role":
            about_lines.append(strip_markdown(line))
            keyword_sources.append(line)
            continue
        if line.startswith("- "):
            claim = strip_markdown(line[2:])
            keyword_sources.append(claim)
            if current_h2 == "Requirements":
                category = "preferred"
                lower_h3 = current_h3.lower()
                if "must" in lower_h3:
                    category = "must_have"
                elif "bonus" in lower_h3:
                    category = "bonus"

                requirement = RequirementItem(
                    id=str(uuid.uuid4()),
                    text=claim,
                    category=category,  # type: ignore[arg-type]
                    keywords=extract_keywords(claim)[:8],
                )
                if category == "must_have":
                    must_have.append(requirement)
                else:
                    preferred.append(requirement)
            elif current_h2 == "What You'll Do":
                themes.append(claim)

    keywords = dedupe_preserve_order(
        extract_keywords(" ".join(keyword_sources + themes + about_lines))
    )

    return JobBrief(
        job_title=title,
        company=company,
        seniority=seniority,
        must_have=must_have,
        preferred=preferred,
        keywords=keywords[:20],
        themes=themes,
        domain_context=" ".join(about_lines).strip() or None,
        raw_text=doc.content,
    )


def _score_requirement_match(requirement: RequirementItem, evidence: EvidenceItem) -> float:
    requirement_text = requirement.text
    evidence_text = " ".join(
        [evidence.claim, evidence.source_excerpt, " ".join(evidence.entities)]
    )

    req_keywords = set(extract_keywords(requirement_text) + requirement.keywords)
    ev_keywords = set(extract_keywords(evidence_text))
    req_concepts = extract_concepts(requirement_text)
    ev_concepts = extract_concepts(evidence_text)

    score = 0.0
    direct_overlap = req_keywords & ev_keywords
    score += len(direct_overlap) * 1.25
    score += len(req_concepts & ev_concepts) * 1.5

    normalized_requirement = normalize_for_matching(requirement_text)
    normalized_evidence = normalize_for_matching(evidence_text)
    specialized_terms = [
        term
        for term in SPECIALIZED_TERMS
        if _contains_normalized_term(normalized_requirement, term)
    ]
    matched_specialized_terms = [
        term
        for term in specialized_terms
        if _contains_normalized_term(normalized_evidence, term)
    ]
    for keyword in req_keywords:
        if _contains_normalized_term(normalized_evidence, keyword):
            score += 0.4

    if evidence.category == "skill" and score:
        score -= 0.25
    elif evidence.category in {"project", "achievement", "leadership", "metric"} and score:
        score += 0.35

    if "llm" in normalized_requirement and any(
        term in normalized_evidence for term in ("claude", "openai", "gemini", "vertex ai")
    ):
        score += 0.75

    if "agent" in normalized_requirement and "agent" in normalized_evidence:
        score += 0.75

    if "telemetry" in normalized_requirement and any(
        term in normalized_evidence for term in ("telemetry", "sensor data", "gps", "airspeed")
    ):
        score += 1.0

    if "cloud" in normalized_requirement and any(
        term in normalized_evidence for term in ("gcp", "cloud run", "cloud sql", "cloud storage")
    ):
        score += 0.75

    if specialized_terms:
        if matched_specialized_terms:
            score += len(matched_specialized_terms) * 1.25
        else:
            score *= 0.25

    if req_concepts and not (req_concepts & ev_concepts):
        score *= 0.45

    if evidence.category in {"education", "certification"} and req_concepts:
        score *= 0.6

    return round(score, 2)


def build_coverage_map_fallback(brief: JobBrief, evidence: list[EvidenceItem]) -> CoverageMap:
    entries: list[CoverageEntry] = []
    all_requirements = brief.must_have + brief.preferred

    for requirement in all_requirements:
        scored = [
            (_score_requirement_match(requirement, item), item)
            for item in evidence
        ]
        scored = [pair for pair in scored if pair[0] > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top_matches = scored[:3]

        top_score = top_matches[0][0] if top_matches else 0.0
        strength = "missing"
        if top_score >= 3.0 and any(
            item.category in {"project", "achievement", "leadership", "metric", "role"}
            for _, item in top_matches
        ):
            strength = "strong"
        elif top_score >= 2.0 and any(
            item.category in {"project", "achievement", "leadership", "metric", "role"}
            for _, item in top_matches
        ):
            strength = "strong"
        elif top_score >= 1.75:
            strength = "weak"
        elif top_score >= 0.75:
            strength = "adjacent"

        evidence_ids = [item.id for _, item in top_matches]
        notes = None
        if top_matches:
            matched_labels = ", ".join(item.claim for _, item in top_matches[:2])
            notes = f"Top supporting evidence: {matched_labels}"

        entries.append(
            CoverageEntry(
                requirement_id=requirement.id,
                strength=strength,  # type: ignore[arg-type]
                evidence_ids=evidence_ids,
                notes=notes,
            )
        )

    total = len(entries)
    points = sum(
        {"strong": 1.0, "weak": 0.5, "adjacent": 0.25, "missing": 0.0}[entry.strength]
        for entry in entries
    )

    return CoverageMap(
        job_id=brief.job_title,
        entries=entries,
        coverage_score=round(points / total, 2) if total else 0.0,
    )


def _trim_sentence(text: str, limit: int = 30) -> str:
    words = text.split()
    if len(words) <= limit:
        return text.rstrip(".") + "."
    return " ".join(words[:limit]).rstrip(",.") + "..."


def _clean_claim_for_bullet(claim: str) -> str:
    cleaned = strip_markdown(claim)
    if ":" in cleaned and cleaned.split(":", 1)[0].istitle():
        cleaned = cleaned.split(":", 1)[1].strip()
    cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
    return cleaned.rstrip(".")


def _pick_primary_evidence(items: list[EvidenceItem]) -> EvidenceItem:
    ranked = sorted(
        items,
        key=lambda item: (
            item.category == "skill",
            item.category not in {"metric", "achievement", "leadership", "project"},
            -len(item.claim),
        ),
    )
    return ranked[0]


def _build_bullet_text(
    primary: EvidenceItem,
    requirement: RequirementItem | None,
    variant: str,
    supporting: list[EvidenceItem],
) -> str:
    base = _clean_claim_for_bullet(primary.claim)
    requirement_terms = extract_keywords(requirement.text)[:2] if requirement else []
    evidence_text = " ".join(item.claim for item in supporting)

    if variant == "technical_depth" and requirement_terms:
        missing_terms = [
            term for term in requirement_terms
            if normalize_for_matching(term) not in normalize_for_matching(base)
            and normalize_for_matching(term) in normalize_for_matching(evidence_text)
        ]
        if missing_terms:
            base = f"{base} using {', '.join(missing_terms[:2])}"
    elif variant == "leadership_forward" and not base.lower().startswith(STRONG_VERBS):
        base = f"Led {base[0].lower() + base[1:]}"
    elif variant == "business_impact":
        impact_source = next(
            (
                item.claim
                for item in supporting
                if any(term in item.claim.lower() for term in ("reduce", "save", "minutes", "days", "%"))
            ),
            "",
        )
        if impact_source and normalize_for_matching(impact_source) not in normalize_for_matching(base):
            base = f"{base}; {impact_source.rstrip('.')}"

    return _trim_sentence(base)


def build_bullet_candidates_fallback(
    coverage_map: CoverageMap,
    brief: JobBrief,
    evidence: list[EvidenceItem],
) -> list[BulletCandidate]:
    evidence_by_id = {item.id: item for item in evidence}
    requirement_by_id = {item.id: item for item in brief.must_have + brief.preferred}
    bullets: list[BulletCandidate] = []
    covered_ids: set[str] = set()
    seen_text: set[str] = set()

    for entry in coverage_map.entries:
        if entry.strength == "missing":
            continue
        matched = [evidence_by_id[item_id] for item_id in entry.evidence_ids if item_id in evidence_by_id]
        if not matched:
            continue

        requirement = requirement_by_id.get(entry.requirement_id)
        primary = _pick_primary_evidence(matched)
        variants = ["balanced"]
        if any(extract_metric_tokens(item.claim) for item in matched):
            variants.append("metric_forward")
        if any(item.category == "leadership" for item in matched):
            variants.append("leadership_forward")
        elif requirement and extract_keywords(requirement.text):
            variants.append("technical_depth")

        for variant in dedupe_preserve_order(variants):
            text = _build_bullet_text(primary, requirement, variant, matched)
            normalized = normalize_for_matching(text)
            if normalized in seen_text:
                continue
            seen_text.add(normalized)
            bullets.append(
                BulletCandidate(
                    evidence_ids=[item.id for item in matched],
                    text=text,
                    variant=variant,  # type: ignore[arg-type]
                    target_requirement_id=entry.requirement_id,
                    provenance_notes=entry.notes,
                )
            )

        covered_ids.update(entry.evidence_ids)

    untied = [
        item for item in evidence
        if item.id not in covered_ids and item.category != "skill"
    ]
    for item in untied[:3]:
        text = _trim_sentence(_clean_claim_for_bullet(item.claim))
        normalized = normalize_for_matching(text)
        if normalized in seen_text:
            continue
        seen_text.add(normalized)
        bullets.append(
            BulletCandidate(
                evidence_ids=[item.id],
                text=text,
                variant="balanced",
                provenance_notes="General supporting evidence",
            )
        )

    return bullets


def group_evidence_by_category(evidence: list[EvidenceItem]) -> dict[str, list[EvidenceItem]]:
    grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        grouped[item.category].append(item)
    return dict(grouped)
