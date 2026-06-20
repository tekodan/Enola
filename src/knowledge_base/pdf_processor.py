"""PDF processor module."""

import re
from pathlib import Path

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from PyPDF2 import PdfReader

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class PDFProcessor:
    """Processor for extracting text from PDF documents."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize PDF processor.

        Args:
            chunk_size: Target size of chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Try pdfplumber first (better for tables)
        if HAS_PDFPLUMBER:
            try:
                return self._extract_with_pdfplumber(pdf_path)
            except Exception:
                pass

        # Fallback to PyPDF2
        if HAS_PYPDF:
            try:
                return self._extract_with_pypdf2(pdf_path)
            except Exception:
                pass

        raise RuntimeError("No PDF library available. Install pdfplumber or PyPDF2.")

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber."""
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2."""
        text_parts = []

        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def chunk_text(
        self, text: str, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> list[str]:
        """Split text into chunks.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size (uses default if None)
            chunk_overlap: Chunk overlap (uses default if None)

        Returns:
            List of text chunks
        """
        size = chunk_size or self.chunk_size
        overlap = chunk_overlap or self.chunk_overlap

        if not text:
            return []

        # Clean text
        text = self._clean_text(text)

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If single paragraph is too long, split by sentences
            if len(para) > size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            # Start new chunk with overlap
                            overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
                            current_chunk = overlap_text + sentence
                        else:
                            # Very long sentence, force split
                            chunks.append(sentence[:size])
                            current_chunk = sentence[size:]
                    else:
                        current_chunk += " " + sentence
            # Normal case
            elif len(current_chunk) + len(para) > size:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-overlap:] if overlap > 0 and current_chunk else ""
                current_chunk = overlap_text + para
            else:
                current_chunk += " " + para

        # Don't forget last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove non-printable characters
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()

    def process_document(self, pdf_path: str, source_name: str | None = None) -> list[dict]:
        """Process a PDF document and return chunks with metadata.

        Args:
            pdf_path: Path to PDF file
            source_name: Optional source name for metadata

        Returns:
            List of chunks with metadata
        """
        text = self.extract_text_from_pdf(pdf_path)
        chunks = self.chunk_text(text)

        source = source_name or Path(pdf_path).stem

        return [
            {
                "text": chunk,
                "metadata": {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
            for i, chunk in enumerate(chunks)
        ]


def extract_text_from_pdf(pdf_path: str) -> str:
    """Convenience function for extracting text from PDF."""
    processor = PDFProcessor()
    return processor.extract_text_from_pdf(pdf_path)


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Convenience function for chunking text."""
    processor = PDFProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return processor.chunk_text(text)
