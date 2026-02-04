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
    iterations = 0
    max_iterations = text_length * 2 + 10  # Safety limit to prevent infinite loops

    while start < text_length and iterations < max_iterations:
        end = min(start + chunk_size, text_length)

        # Extract chunk
        chunk = text[start:end].strip()

        # Only yield if chunk meets minimum size
        if len(chunk) >= min_chunk_size:
            yield (chunk, start, end)

        # If we've reached the end of the text, stop
        if end == text_length:
            break

        # Move to next chunk with overlap
        new_start = end - chunk_overlap

        # Ensure we're making progress
        if new_start <= start:
            logger.warning(
                "chunking_no_progress",
                text_length=text_length,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                start=start,
                new_start=new_start,
            )
            break

        start = new_start
        iterations += 1

    # If we hit the max iterations, it indicates a potential infinite loop
    if iterations >= max_iterations:
        logger.warning(
            "chunking_iteration_limit_reached",
            text_length=text_length,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
            iterations=iterations,
        )


def create_chunks(document: Document, config: ChunkingConfig) -> list[Chunk]:
    """Create chunks from a document.

    Args:
        document: Document to chunk
        config: Chunking configuration

    Returns:
        List of chunks
    """
    chunks = []

    for idx, (text_content, start_char, end_char) in enumerate(
        chunk_text(
            document.content,
            config.chunk_size,
            config.chunk_overlap,
            config.min_chunk_size,
        )
    ):
        chunk = Chunk(
            repository_id=document.repository_id,
            document_id=document.id,
            content=text_content,
            chunk_index=idx,
            start_char=start_char,
            end_char=end_char,
        )
        chunks.append(chunk)

    logger.info(
        "document_chunked",
        document_id=str(document.id),
        chunk_count=len(chunks),
        avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
    )

    return chunks
