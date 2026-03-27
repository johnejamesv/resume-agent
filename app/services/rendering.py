"""Resume rendering to markdown and plain text."""

from __future__ import annotations

from app.schemas.resume import ResumeDraft


def render_markdown(draft: ResumeDraft) -> str:
    """Render a ResumeDraft as clean markdown."""
    lines: list[str] = []

    lines.append(f"# {draft.candidate_name}")
    lines.append(f"*Target: {draft.target_job}*")
    lines.append("")

    sorted_sections = sorted(draft.sections, key=lambda s: s.order)
    for section in sorted_sections:
        lines.append(f"## {section.heading}\n")
        for bullet in section.bullets:
            lines.append(f"- {bullet.text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_plaintext(draft: ResumeDraft) -> str:
    """Render a ResumeDraft as plain text (no markdown syntax)."""
    lines: list[str] = []

    lines.append(draft.candidate_name.upper())
    lines.append(f"Target: {draft.target_job}")
    lines.append("")

    sorted_sections = sorted(draft.sections, key=lambda s: s.order)
    for section in sorted_sections:
        lines.append(f"{section.heading.upper()}\n")
        for bullet in section.bullets:
            lines.append(f"  * {bullet.text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
