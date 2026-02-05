"""Markdown-aware chunking utilities.

This module provides intelligent chunking for Markdown documents that respects
the semantic structure of Markdown, including:
- Headings and their content
- Paragraphs
- Lists
- Code blocks
- Tables
- Blockquotes
"""

import re

from memory.config.schema import ChunkingConfig
from memory.core.models import Chunk, Document
from memory.observability.logging import get_logger

logger = get_logger(__name__)


class MarkdownChunk:
    """Represents a semantic chunk in a Markdown document."""

    def __init__(self, content: str, level: int = 0, chunk_type: str = "content"):
        self.content = content
        self.level = level  # Heading level (1-6) or 0 for non-heading
        self.type = chunk_type  # 'heading', 'paragraph', 'list', 'code', 'table', 'blockquote'

    @property
    def is_heading(self) -> bool:
        return self.level > 0

    @property
    def is_code_block(self) -> bool:
        return self.type == "code"

    @property
    def is_list(self) -> bool:
        return self.type == "list"

    @property
    def char_count(self) -> int:
        return len(self.content)


def parse_markdown_sections(text: str) -> list[MarkdownChunk]:
    """Parse Markdown document into semantic sections.

    Args:
        text: Markdown text content

    Returns:
        List of MarkdownChunk objects representing semantic sections
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")
    chunks: list[MarkdownChunk] = []
    current_chunk: list[str] = []
    current_type = "content"
    current_level = 0
    in_code_block = False

    for line in lines:
        # Check for code block fences
        if line.strip().startswith("```"):
            if not in_code_block:
                # Start of code block
                if current_chunk:
                    chunks.append(
                        MarkdownChunk("\n".join(current_chunk), current_level, current_type)
                    )
                current_chunk = [line]
                in_code_block = True
                current_type = "code"
                current_level = 0
                code_fence = line.strip()
            else:
                # End of code block
                current_chunk.append(line)
                chunks.append(MarkdownChunk("\n".join(current_chunk), 0, "code"))
                current_chunk = []
                in_code_block = False
                current_type = "content"
                current_level = 0
                code_fence = None
            continue

        if in_code_block:
            current_chunk.append(line)
            continue

        # Check for headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if heading_match:
            # Save previous chunk if exists
            if current_chunk:
                chunks.append(MarkdownChunk("\n".join(current_chunk), current_level, current_type))

            # Start new heading chunk
            level = len(heading_match.group(1))
            content = heading_match.group(2)
            chunks.append(MarkdownChunk(content, level, "heading"))

            # Next content belongs to this heading
            current_chunk = []
            current_type = "content"
            current_level = 0  # Content chunks should have level 0
            continue

        # Check for list items
        list_match = re.match(r"^(\s*[-*+]\s+|\s*\d+\.\s+)(.+)$", line)
        if list_match:
            if current_type != "list":
                # Save previous chunk if exists
                if current_chunk:
                    chunks.append(
                        MarkdownChunk("\n".join(current_chunk), current_level, current_type)
                    )
                current_type = "list"
                current_chunk = [list_match.group(2)]
            else:
                # Continue list
                current_chunk.append(list_match.group(2))
            continue

        # Check for blockquotes
        if line.strip().startswith(">"):
            if current_type != "blockquote":
                # Save previous chunk if exists
                if current_chunk:
                    chunks.append(
                        MarkdownChunk("\n".join(current_chunk), current_level, current_type)
                    )
                current_type = "blockquote"
                current_chunk = [line.strip()[1:].strip()]
            else:
                current_chunk.append(line.strip()[1:].strip())
            continue

        # Check for horizontal rules
        if re.match(r"^\s*[-*_]{3,}\s*$", line):
            if current_chunk:
                chunks.append(MarkdownChunk("\n".join(current_chunk), current_level, current_type))
            chunks.append(MarkdownChunk("---", 0, "hr"))
            current_chunk = []
            current_type = "content"
            current_level = 0
            continue

        # Regular content
        if line.strip():
            if current_type != "content":
                # Save previous chunk if exists
                if current_chunk:
                    chunks.append(
                        MarkdownChunk("\n".join(current_chunk), current_level, current_type)
                    )
                current_type = "content"
                current_chunk = [line.strip()]
            else:
                current_chunk.append(line.strip())

    # Save final chunk
    if current_chunk:
        chunks.append(MarkdownChunk("\n".join(current_chunk), current_level, current_type))

    return chunks


def smart_merge_chunks(chunks: list[MarkdownChunk], target_size: int, overlap: int) -> list[str]:
    """Intelligently merge Markdown chunks while preserving semantic boundaries.

    Args:
        chunks: List of MarkdownChunk objects
        target_size: Target chunk size in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of merged chunk texts
    """
    if not chunks:
        return []

    merged_chunks: list[str] = []
    current_chunk_content: list[str] = []
    current_chunk_size = 0
    current_heading_context = ""  # Keep track of current heading for context

    for chunk in chunks:
        # Skip horizontal rules as separate chunks
        if chunk.type == "hr":
            if current_chunk_content:
                merged_text = "\n\n".join(current_chunk_content)
                if len(merged_text) >= 100:  # min_chunk_size
                    merged_chunks.append(merged_text)
                current_chunk_content = []
                current_chunk_size = 0
            continue

        chunk_text = chunk.content

        # Add heading context for non-heading chunks
        if not chunk.is_heading and chunk.type == "content" and current_heading_context:
            chunk_text = f"{current_heading_context}\n\n{chunk_text}"

        # Check if adding this chunk would exceed target size
        new_size = current_chunk_size + len(chunk_text) + 2  # +2 for \n\n

        if new_size > target_size and current_chunk_content:
            # Current chunk is full, save it and start new one
            merged_text = "\n\n".join(current_chunk_content)
            if len(merged_text) >= 100:  # min_chunk_size
                merged_chunks.append(merged_text)

            # Start new chunk with overlap
            if overlap > 0 and current_chunk_content:
                # Get last part for overlap
                last_content = current_chunk_content[-1]
                overlap_text = (
                    last_content[-overlap:] if len(last_content) > overlap else last_content
                )
                current_chunk_content = [overlap_text]
                current_chunk_size = len(overlap_text)
            else:
                current_chunk_content = []
                current_chunk_size = 0

        # Add chunk to current
        if current_chunk_content:
            current_chunk_content.append(chunk_text)
            current_chunk_size += len(chunk_text) + 2  # +2 for \n\n
        else:
            current_chunk_content.append(chunk_text)
            current_chunk_size = len(chunk_text)

        # Update heading context
        if chunk.is_heading:
            # Keep full heading with level
            current_heading_context = "#" * chunk.level + " " + chunk.content
        elif chunk.type != "content":
            # Non-content chunks don't update heading context
            pass
        else:
            # Content chunks can exist without explicit heading
            if not current_heading_context:
                current_heading_context = "Document"

    # Add final chunk
    if current_chunk_content:
        merged_text = "\n\n".join(current_chunk_content)
        if len(merged_text) >= 100:  # min_chunk_size
            merged_chunks.append(merged_text)
        elif merged_text:  # Even if small, add it if not empty
            merged_chunks.append(merged_text)

    # If no chunks were created, at least return the original text
    if not merged_chunks and chunks:
        # Fallback: create a single chunk from all content
        full_text = "\n\n".join([c.content for c in chunks])
        if full_text:
            merged_chunks.append(full_text)

    return merged_chunks


def chunk_markdown_document(document: Document, config: ChunkingConfig) -> list[Chunk]:
    """Create intelligent chunks from a Markdown document.

    This function respects Markdown semantics and creates more coherent chunks
    for embedding and retrieval.

    Args:
        document: Document to chunk (should be Markdown type)
        config: Chunking configuration

    Returns:
        List of Chunk objects
    """
    # Parse into semantic sections
    semantic_chunks = parse_markdown_sections(document.content)

    if not semantic_chunks:
        logger.warning(
            "no_markdown_sections_parsed",
            document_id=str(document.id),
        )
        return []

    # Merge intelligently
    merged_texts = smart_merge_chunks(semantic_chunks, config.chunk_size, config.chunk_overlap)

    # Create Chunk objects
    chunks: list[Chunk] = []
    for idx, text in enumerate(merged_texts):
        # Find the position in original text
        start_char = document.content.find(text[:50])  # Use first 50 chars as anchor
        if start_char == -1:
            # Fallback: use character count based on chunk index
            start_char = idx * (config.chunk_size - config.chunk_overlap)
            start_char = min(start_char, len(document.content))
        end_char = min(start_char + len(text), len(document.content))

        chunk = Chunk(
            repository_id=document.repository_id,
            document_id=document.id,
            content=text,
            chunk_index=idx,
            start_char=start_char,
            end_char=end_char,
        )
        chunks.append(chunk)

    logger.info(
        "markdown_document_chunked",
        document_id=str(document.id),
        semantic_chunks=len(semantic_chunks),
        final_chunks=len(chunks),
        avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
    )

    return chunks
