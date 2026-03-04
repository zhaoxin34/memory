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
from memory.core.logging import get_logger
from memory.entities import Chunk, Document

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
            else:
                # End of code block
                current_chunk.append(line)
                chunks.append(MarkdownChunk("\n".join(current_chunk), 0, "code"))
                current_chunk = []
                in_code_block = False
                current_type = "content"
                current_level = 0
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


def smart_merge_chunks(
    chunks: list[MarkdownChunk], target_size: int, overlap: int, min_chunk_size: int = 100
) -> list[str]:
    """Intelligently merge Markdown chunks while preserving semantic boundaries.

    Args:
        chunks: List of MarkdownChunk objects
        target_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size to save (default 100)

    Returns:
        List of merged chunk texts
    """
    if not chunks:
        return []

    merged_chunks: list[str] = []
    current_chunk_content: list[str] = []
    current_chunk_size = 0

    # Track heading hierarchy: list of (level, heading_text)
    # This preserves the full heading chain from H1 to current heading
    heading_stack: list[tuple[int, str]] = []

    # Helper to generate heading context from stack
    def get_heading_context() -> str:
        if not heading_stack:
            return ""
        return "\n\n".join(["#" * level + " " + text for level, text in heading_stack])

    # Track the level of the previous heading to enforce heading boundary
    previous_heading_level = 0

    # Helper to save current chunk if it meets minimum size
    def save_current_chunk() -> None:
        nonlocal current_chunk_content, current_chunk_size, previous_heading_level
        if not current_chunk_content:
            return
        merged_text = "\n\n".join(current_chunk_content)
        if len(merged_text) >= min_chunk_size:
            merged_chunks.append(merged_text)
        current_chunk_content = []
        current_chunk_size = 0
        previous_heading_level = 0

    for chunk in chunks:
        # Skip horizontal rules as separate chunks
        if chunk.type == "hr":
            save_current_chunk()
            continue

        chunk_text = chunk.content

        # Update heading stack when encountering a heading
        # This happens BEFORE we decide what to do with the chunk
        if chunk.is_heading:
            # Remove any headings at the same or lower level
            heading_stack = [(level, text) for level, text in heading_stack if level < chunk.level]
            # Remove duplicate at same level if exists (e.g., multiple "## 新增功能")
            # Use (level, content) pair for deduplication
            heading_stack = [
                (level, text) for level, text in heading_stack
                if not (level == chunk.level and text == chunk.content)
            ]
            # Add current heading
            heading_stack.append((chunk.level, chunk.content))

            # If we encounter a heading at a higher level in the hierarchy (smaller number)
            # and there's content in current chunk, save the current chunk first to maintain semantic boundaries
            # e.g., moving from ### (level 3) to ## (level 2) or # (level 1) should start a new chunk
            # But ### to ### (same level) should NOT start a new chunk
            if current_chunk_content and previous_heading_level > 0 and chunk.level < previous_heading_level:
                save_current_chunk()

        # Add heading context ONLY when starting a new merged chunk with content
        # - If current_chunk_content is empty, we're starting a new merged chunk
        # - For heading chunks in new chunks: use full heading chain (heading already in stack)
        # - For content chunks in new chunks: use full heading chain as prefix
        # - For subsequent chunks (not new): just append without extra heading context
        is_new_chunk = len(current_chunk_content) == 0

        # Always update previous_heading_level when encountering a heading
        # This is needed to track the last heading we saw for boundary checking
        if chunk.is_heading:
            previous_heading_level = chunk.level

        if is_new_chunk:

            heading_context = get_heading_context()
            if heading_context:
                if chunk.is_heading:
                    # For heading in new chunk: heading_context already includes this heading
                    # Use as-is (no need to add again)
                    chunk_text = heading_context
                else:
                    # For content in new chunk: prepend heading context
                    chunk_text = f"{heading_context}\n\n{chunk_text}"
        elif chunk.is_heading:
            # For heading that follows other content in the same chunk:
            # Check if this heading is already at the end of heading_stack
            # (can happen with duplicate headings like multiple "## 新增功能")
            # If so, heading_context already has this heading, so just add the heading text
            # without parent context to avoid duplication
            if heading_stack and heading_stack[-1][0] == chunk.level and heading_stack[-1][1] == chunk.content:
                # Heading already at end of stack, it's already in heading_context
                pass
            else:
                # Add parent heading context (all headings except the current one)
                parent_context = "\n\n".join(
                    ["#" * level + " " + text for level, text in heading_stack[:-1]]
                )
                if parent_context:
                    chunk_text = f"{parent_context}\n\n{chunk_text}"

        # Check if adding this chunk would exceed target size
        new_size = current_chunk_size + len(chunk_text) + 2  # +2 for \n\n

        if new_size > target_size and current_chunk_content:
            # Current chunk is full, save it and start new one
            merged_text = "\n\n".join(current_chunk_content)
            if len(merged_text) >= min_chunk_size:
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
                previous_heading_level = 0  # Reset heading level for overlap chunk
            else:
                current_chunk_content = []
                current_chunk_size = 0
                previous_heading_level = 0

        # Add chunk to current
        if current_chunk_content:
            current_chunk_content.append(chunk_text)
            current_chunk_size += len(chunk_text) + 2  # +2 for \n\n
        else:
            current_chunk_content.append(chunk_text)
            current_chunk_size = len(chunk_text)

    # Add final chunk
    if current_chunk_content:
        merged_text = "\n\n".join(current_chunk_content)
        if len(merged_text) >= min_chunk_size:
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
    # If document has a title and content doesn't start with H1, prepend title as H1
    content = document.content
    if document.title:
        # Check if content already starts with a level 1 heading
        first_line = content.lstrip().split("\n")[0] if content else ""
        if not first_line.startswith("# "):
            # Prepend title as H1
            content = f"# {document.title}\n\n{content}"

    # Parse into semantic sections
    semantic_chunks = parse_markdown_sections(content)

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
        # Find the position in original text using a more robust approach
        start_char = -1
        # Try to find the exact text first
        start_char = document.content.find(text)

        if start_char == -1:
            # If exact match fails, try first 50 chars as anchor
            anchor = text[:50]
            start_char = document.content.find(anchor)

        if start_char == -1:
            # Fallback: estimate position based on chunk index
            # This is less accurate but ensures we don't crash
            estimated_pos = idx * (config.chunk_size - config.chunk_overlap)
            start_char = min(estimated_pos, len(document.content) - 1)

        # Ensure end_char is always > start_char
        end_char = min(start_char + len(text), len(document.content))
        if end_char <= start_char:
            # Guarantee at least 1 character difference
            end_char = min(start_char + 1, len(document.content))

        # Determine the semantic type of this chunk by analyzing its content
        chunk_type = detect_chunk_type(text)

        # Store semantic type in metadata for later reference
        chunk_metadata = {"chunk_type": chunk_type}

        chunk = Chunk(
            repository_id=document.repository_id,
            document_id=document.id,
            content=text,
            chunk_index=idx,
            start_char=start_char,
            end_char=end_char,
            metadata=chunk_metadata,
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


def detect_chunk_type(text: str) -> str:
    """Detect the semantic type of a Markdown chunk.

    This is a heuristic - we check the primary content type of the chunk.

    Args:
        text: The chunk text content

    Returns:
        The detected chunk type: 'content', 'heading', 'code', 'list', 'blockquote', or 'hr'
    """
    chunk_type = "content"  # default
    lines = text.split('\n')
    first_line = lines[0].strip() if lines else ""

    # Check if it's primarily a heading
    if first_line.startswith("#"):
        chunk_type = "heading"
    # Check if it's primarily a code block
    elif "```" in text:
        # Check if more than half the content is code
        code_lines = sum(1 for line in lines if line.startswith("    ") or "```" in line)
        if code_lines > len(lines) / 2:
            chunk_type = "code"
    # Check if it's primarily a list
    elif (text.strip().startswith("-") or text.strip().startswith("*") or
          text.strip().startswith("+") or re.match(r"^\d+\.", text.strip())):
        # Check if multiple lines are list items
        list_lines = sum(1 for line in lines if (line.strip().startswith("-") or
                                                  line.strip().startswith("*") or
                                                  line.strip().startswith("+") or
                                                  re.match(r"^\s*\d+\.", line)))
        if list_lines > len(lines) / 2:
            chunk_type = "list"
    # Check if it's primarily a blockquote
    elif text.strip().startswith(">"):
        quote_lines = sum(1 for line in lines if line.strip().startswith(">"))
        if quote_lines > len(lines) / 2:
            chunk_type = "blockquote"
    # Check if it's a horizontal rule
    elif text.strip() == "---":
        chunk_type = "hr"

    return chunk_type
