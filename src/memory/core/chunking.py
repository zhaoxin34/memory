"""Text chunking utilities.

Why this exists:
- Splits documents into embedding-sized chunks
- Maintains context with overlapping windows
- Preserves semantic boundaries where possible

How to extend:
- Add semantic chunking (sentence/paragraph boundaries)
- Add language-specific chunking
- Add code-aware chunking

Specialized chunking:
- Markdown-aware chunking for .md files (preserves headings, paragraphs, lists)
"""

from collections.abc import Iterator

from memory.config.schema import ChunkingConfig
from memory.core.logging import get_logger
from memory.entities import Chunk, Document, DocumentType

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

    Uses specialized chunking strategies based on document type:
    - Markdown documents: Uses tree-sitter semantic chunking (falls back to regex-based)
    - Other documents: Uses fixed-size chunking with overlap

    Args:
        document: Document to chunk
        config: Chunking configuration

    Returns:
        List of chunks
    """
    # Use tree-sitter based chunking for Markdown documents (preferred)
    if document.doc_type == DocumentType.MARKDOWN:
        # Try tree-sitter chunking first
        try:
            from memory.core.tree_sitter_chunking import tree_sitter_chunk_document
            chunks = tree_sitter_chunk_document(document, config)
            if chunks:
                logger.info(
                    "document_chunked_with_tree_sitter",
                    document_id=str(document.id),
                    document_type=document.doc_type.value,
                    chunk_count=len(chunks),
                    avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
                )
                return chunks
        except ImportError:
            logger.debug("tree_sitter_not_available_using_fallback")
        except Exception as e:
            logger.warning(
                "tree_sitter_chunking_failed",
                document_id=str(document.id),
                error=str(e),
            )

        # Fallback to regex-based markdown chunking
        try:
            from memory.core.markdown_chunking import chunk_markdown_document
            chunks = chunk_markdown_document(document, config)
            if chunks:
                logger.info(
                    "document_chunked_with_regex",
                    document_id=str(document.id),
                    document_type=document.doc_type.value,
                    chunk_count=len(chunks),
                    avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
                )
                return chunks
        except ImportError as e:
            logger.debug(
                "markdown_chunking_fallback_failed",
                document_id=str(document.id),
                error=str(e),
            )

    # Default: Use fixed-size chunking for non-Markdown documents
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
        document_type=document.doc_type.value if document.doc_type else "unknown",
        chunk_count=len(chunks),
        avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
    )

    return chunks
