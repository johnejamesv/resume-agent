from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.schemas.evidence import SourceDocument
from app.graph import run_pipeline


def _read_file(path: str) -> str:
    """Read a file and return its contents as a string."""
    return Path(path).read_text(encoding="utf-8")


def _build_source(path: str) -> SourceDocument:
    """Create a SourceDocument from a file path, guessing source_type from extension."""
    content = _read_file(path)
    name = Path(path).name.lower()

    if "resume" in name:
        source_type = "resume"
    elif "linkedin" in name:
        source_type = "linkedin"
    elif "brag" in name:
        source_type = "brag_doc"
    elif "transcript" in name:
        source_type = "transcript"
    elif "review" in name:
        source_type = "performance_review"
    elif "project" in name:
        source_type = "project_summary"
    elif "notes" in name:
        source_type = "notes"
    else:
        source_type = "other"

    return SourceDocument(content=content, filename=Path(path).name, source_type=source_type)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evidence-grounded agentic resume builder",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="Paths to candidate source files (resumes, transcripts, brag docs, etc.)",
    )
    parser.add_argument(
        "--jobs",
        nargs="+",
        required=True,
        help="Paths to job description files",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> None:
    sources = [_build_source(p) for p in args.sources]
    job_texts = [_read_file(p) for p in args.jobs]

    print(f"Loaded {len(sources)} source(s) and {len(job_texts)} job description(s).\n")

    result = await run_pipeline(sources=sources, job_texts=job_texts)

    print("\n--- Export Outputs ---")
    outputs = result.get("export_outputs", {})
    if not outputs:
        print("(no export outputs produced -- stubs only)")
    for fmt, content in outputs.items():
        print(f"\n[{fmt}]\n{content}")

    errors = result.get("errors", [])
    if errors:
        print("\n--- Errors ---")
        for err in errors:
            print(f"  - {err}")


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
