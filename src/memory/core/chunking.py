"""Text chunking utilities.

Why this exists:
- Splits documents into embedding-sized chunks
- Maintains context with overlapping windows
- Preserves semantic boundaries where possible

How to extend:
- Add semantic chunking (sentence/paragraph boundaries)
- Add language-specific chunking
- Add code-aware chunking
"""

from typing import Iterator

from memory.config.schema import ChunkingConfig
from memory.core.models import Chunk, Document
from memory.observability.logging import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    min_chunk_size: int,
) -> Iterator[tuple[str, int, int]]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size (discard smaller chunks)

    Yields:
        Tuples of (chunk_text, start_char, end_char)
    """
    if not text or not text.strip():
        return

    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Extract chunk
        chunk = text[start:end].strip()

        # Only yield if chunk meets minimum size
        if len(chunk) >= min_chunk_size:
            yield (chunk, start, end)

        # Move to next chunk with overlap
        start = end - chunk_overlap

        # Prevent infinite loop if overlap >= chunk_size
        if start <= end - chunk_size:
            start = end


def create_chunks(document: Document, config: ChunkingConfig) -> list[Chunk]:
    """Create chunks from a document.

    Args:
        document: Document to chunk
        config: Chunking configuration

    Returns:
        List of chunks
    """
    chunks = []

    for idx, (chunk_text, start_char, end_char) in enumerate(
        chunk_text(
            document.content,
            config.chunk_size,
            config.chunk_overlap,
            config.min_chunk_size,
        )
    ):
        chunk = Chunk(
            document_id=document.id,
            content=chunk_text,
            chunk_index=idx,
            start_char=start_char,
            end_char=end_char,
            metadata={
                "document_title": document.title,
                "document_type": document.doc_type,
                "source_path": document.source_path,
            },
        )
        chunks.append(chunk)

    logger.info(
        "document_chunked",
        document_id=str(document.id),
        chunk_count=len(chunks),
        avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
    )

    return chunks
