"""Text extraction and normalization utilities.

Stub for future PDF/docx parsing — currently handles plain text cleanup.
"""

from __future__ import annotations

import re


def extract_text(content: str, source_type: str = "text") -> str:
    """Normalize input text: strip whitespace, collapse newlines.

    Parameters
    ----------
    content:
        Raw input string (later: bytes for PDF/docx).
    source_type:
        Hint for future format-specific parsing (e.g. "pdf", "docx", "text").
    """
    _ = source_type  # reserved for future dispatch
    text = content.strip()
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text
