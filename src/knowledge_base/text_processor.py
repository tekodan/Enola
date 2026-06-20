"""Text processor for .md and .txt files.

Extracts plain text, strips markdown, splits into chunks,
and generates metadata for ChromaDB ingestion.
"""

import re
from datetime import datetime

from src.knowledge_base.pdf_processor import chunk_text as _chunk_text


def strip_markdown(text: str) -> str:
    """Remove markdown syntax, keep structural content.

    Strips heading markers, bold/italic, code fences, links, images, lists, HR, tables.
    """
    lines = text.split("\n")
    cleaned = []

    in_code_block = False

    for line in lines:
        # Toggle code fences
        if re.match(r"^```", line.strip()):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            cleaned.append(line)
            continue

        stripped_line = line.strip()

        # Strip heading markers
        stripped_line = re.sub(r"^#{1,6}\s+", "", stripped_line)

        # Strip bold/italic markers
        stripped_line = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", stripped_line)
        stripped_line = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", stripped_line)

        # Strip image syntax
        stripped_line = re.sub(r"!\[.*?\]\(.*?\)", "", stripped_line)

        # Strip link, keep text
        stripped_line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped_line)

        # Strip HR
        if re.match(r"^-{3,}$", stripped_line):
            continue

        # Strip blockquote marker
        stripped_line = re.sub(r"^>\s+", "", stripped_line)

        cleaned.append(stripped_line)

    return "\n".join(cleaned)


def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    # Remove non-printable chars (keep newlines)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Collapse multiple blank lines (keep at most one)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_markdown(text: str) -> str:
    """Convert markdown to plain text for embedding."""
    text = strip_markdown(text)
    text = clean_text(text)
    return text


def process_text(
    content: str,
    source: str,
    file_format: str = "md",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Process raw text content into chunks with metadata.

    Args:
        content: Raw file content (markdown or plain text)
        source: Source identifier (typically the filename)
        file_format: ``"md"``, ``"txt"``, or ``"pdf"``
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of dicts with ``text`` and ``metadata`` keys.
    """
    if not content.strip():
        return []

    # Parse markdown → plain text if needed
    if file_format == "md":
        plain = parse_markdown(content)
    else:
        plain = clean_text(content)

    if not plain.strip():
        return []

    chunks = _chunk_text(plain, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    now = datetime.now().isoformat(timespec="seconds")

    return [
        {
            "text": chunk,
            "metadata": {
                "source": source,
                "format": file_format,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "uploaded_at": now,
            },
        }
        for i, chunk in enumerate(chunks)
    ]
