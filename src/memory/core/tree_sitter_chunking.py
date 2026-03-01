"""Tree-sitter based Markdown chunking.

This module provides intelligent chunking for Markdown documents using
tree-sitter for accurate syntax tree parsing, supporting:
- Headings and their content
- Nested lists
- Tables
- Code blocks
- Blockquotes
- Semantic boundary preservation
"""

import re
import signal

from memory.config.schema import ChunkingConfig
from memory.core.logging import get_logger
from memory.entities import Chunk, Document

logger = get_logger(__name__)


def _check_tree_sitter_available() -> bool:
    """Check if tree-sitter is available."""
    try:
        import importlib.util
        return importlib.util.find_spec("tree_sitter") is not None
    except ImportError:
        return False


def _get_tree_sitter_language():
    """Get the tree-sitter language object for markdown."""
    try:
        import tree_sitter
        import tree_sitter_markdown
        # Create Language object from PyCapsule
        return tree_sitter.Language(tree_sitter_markdown.language())
    except ImportError:
        return None


class SemanticNode:
    """Represents a semantic node from the syntax tree."""

    def __init__(
        self,
        node_type: str,
        content: str,
        start_byte: int = 0,
        end_byte: int = 0,
        children: list["SemanticNode"] | None = None,
        metadata: dict | None = None,
    ):
        self.node_type = node_type
        self.content = content
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.children = children or []
        self.metadata = metadata or {}

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def is_heading(self) -> bool:
        return self.node_type in ("atx_heading", "setext_heading")

    @property
    def is_table(self) -> bool:
        return self.node_type == "table"

    @property
    def is_list(self) -> bool:
        return self.node_type in ("bullet_list", "ordered_list", "list_item")

    @property
    def is_code_block(self) -> bool:
        return self.node_type in ("fenced_code_block", "indented_code_block")

    @property
    def is_blockquote(self) -> bool:
        return self.node_type == "block_quote"

    @property
    def is_paragraph(self) -> bool:
        return self.node_type == "paragraph"


def parse_markdown_syntax_tree(text: str) -> SemanticNode | None:
    """Parse Markdown text into a syntax tree using tree-sitter.

    Args:
        text: Markdown text content

    Returns:
        Root SemanticNode of the syntax tree, or None if parsing fails
    """
    if not text or not text.strip():
        return None

    if not _check_tree_sitter_available():
        logger.warning("tree_sitter_not_available")
        return None

    language = _get_tree_sitter_language()
    if language is None:
        logger.warning("tree_sitter_markdown_language_not_available")
        return None

    try:
        import tree_sitter

        # Define timeout exception
        class ParsingTimeoutError(Exception):
            pass

        # Create parser with markdown language
        parser = tree_sitter.Parser()
        parser.language = language

        # Parse with timeout protection (5 seconds)
        def timeout_handler(signum, frame):
            raise ParsingTimeoutError("Parsing timed out")

        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout

        try:
            text_bytes = text.encode("utf-8")
            tree = parser.parse(text_bytes)
        finally:
            signal.alarm(0)  # Cancel alarm

        # Convert to semantic nodes
        root = _tree_to_semantic_node(tree.root_node, text, text_bytes)
        return root

    except ImportError as e:
        logger.warning(
            "tree_sitter_import_error",
            error=str(e),
        )
        return None
    except ParsingTimeoutError:
        logger.warning("tree_sitter_parsing_timeout")
        return None
    except Exception as e:
        logger.warning(
            "tree_sitter_parsing_error",
            error=str(e),
        )
        return None


def _tree_to_semantic_node(node, text: str, text_bytes: bytes = None) -> SemanticNode:
    """Convert a tree-sitter node to a SemanticNode."""
    node_type = node.type

    # Use bytes for slicing (tree-sitter uses byte offsets)
    if text_bytes is None:
        text_bytes = text.encode("utf-8")
    content = text_bytes[node.start_byte : node.end_byte].decode("utf-8") if node.start_byte < node.end_byte else ""

    children = []
    for child in node.children:
        if child.type not in ("ERROR", "WHITESPACE"):
            child_node = _tree_to_semantic_node(child, text, text_bytes)
            children.append(child_node)

    # Extract metadata based on node type
    metadata = {}
    if node_type == "fenced_code_block":
        # Extract language from fence info
        first_child = children[0] if children else None
        if first_child and first_child.node_type == "info_string":
            metadata["language"] = first_child.content.strip()
    elif node_type == "atx_heading":
        # Extract heading level from the opening hashes
        heading_levels = ("heading_h1", "heading_h2", "heading_h3", "heading_h4", "heading_h5", "heading_h6")
        for child in children:
            if child.node_type in heading_levels:
                metadata["level"] = int(child.node_type[-1])

    return SemanticNode(
        node_type=node_type,
        content=content,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        children=children,
        metadata=metadata,
    )


def extract_semantic_nodes(tree: SemanticNode) -> list[SemanticNode]:
    """Extract semantic nodes from the syntax tree.

    This function traverses the tree and extracts meaningful semantic
    units while maintaining structure for context.

    Args:
        tree: Root SemanticNode of the syntax tree

    Returns:
        List of semantic nodes ready for chunking
    """
    if tree is None:
        return []

    nodes: list[SemanticNode] = []

    def traverse(node: SemanticNode, heading_context: list[str] | None = None):
        if node is None:
            return

        # Track heading context
        current_heading_context = heading_context or []
        if node.is_heading:
            level = node.metadata.get("level", 1)
            # Keep only headings of equal or higher level (remove deeper headings)
            current_heading_context = [
                h for h in current_heading_context
                if h["level"] <= level
            ]
            current_heading_context.append({
                "level": level,
                "text": node.content.strip("#").strip()
            })

        # Handle tables - extract as single unit
        if node.is_table:
            nodes.append(_extract_table_node(node, current_heading_context))
        # Handle code blocks
        elif node.is_code_block:
            nodes.append(_extract_code_node(node, current_heading_context))
        # Handle blockquotes
        elif node.is_blockquote:
            nodes.append(_extract_blockquote_node(node, current_heading_context))
        # Handle list items - process their content
        elif node.node_type == "list_item":
            nodes.append(_extract_list_item_node(node, current_heading_context))
        # Handle headings
        elif node.is_heading:
            nodes.append(node)
        # Handle paragraphs and other content
        elif node.is_paragraph:
            nodes.append(_wrap_with_context(node, current_heading_context))
        # Process children
        else:
            for child in node.children:
                traverse(child, current_heading_context)

    traverse(tree)
    return nodes


def _extract_table_node(node: SemanticNode, context: list[dict]) -> SemanticNode:
    """Extract a table as a complete semantic unit."""
    # Build complete table with markdown formatting
    table_content = _reconstruct_table(node)

    # Get text position
    start_byte = node.start_byte
    end_byte = node.end_byte

    return SemanticNode(
        node_type="table",
        content=table_content,
        start_byte=start_byte,
        end_byte=end_byte,
        metadata={
            "chunk_type": "table",
            "heading_context": context,
        },
    )


def _reconstruct_table(node: SemanticNode) -> str:
    """Reconstruct markdown table from syntax tree."""
    lines: list[str] = []

    def process_table_row(row_node: SemanticNode, is_header: bool = False) -> list[str]:
        cells = []
        for child in row_node.children:
            if child.node_type == "table_cell":
                cells.append(child.content.strip())
        return cells

    for child in node.children:
        if child.node_type == "table_header_row":
            cells = process_table_row(child, is_header=True)
            if cells:
                header_line = "| " + " | ".join(cells) + " |"
                separator = "|" + "|".join(["---" for _ in cells]) + "|"
                lines.append(header_line)
                lines.append(separator)
        elif child.node_type == "table_row":
            cells = process_table_row(child)
            if cells:
                row_line = "| " + " | ".join(cells) + " |"
                lines.append(row_line)

    return "\n".join(lines)


def _extract_code_node(node: SemanticNode, context: list[dict]) -> SemanticNode:
    """Extract a code block as a semantic unit."""
    return SemanticNode(
        node_type="code",
        content=node.content,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        metadata={
            "chunk_type": "code",
            "heading_context": context,
            "language": node.metadata.get("language", ""),
        },
    )


def _extract_blockquote_node(node: SemanticNode, context: list[dict]) -> SemanticNode:
    """Extract a blockquote as a semantic unit."""
    return SemanticNode(
        node_type="blockquote",
        content=node.content,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        metadata={
            "chunk_type": "blockquote",
            "heading_context": context,
        },
    )


def _extract_list_item_node(node: SemanticNode, context: list[dict]) -> SemanticNode:
    """Extract a list item with its content."""
    content_parts: list[str] = []

    for child in node.children:
        if child.node_type in ("bullet_list_marker", "ordered_list_marker"):
            content_parts.append(child.content)
        elif child.node_type == "paragraph":
            content_parts.append(child.content)
        elif child.node_type in ("bullet_list", "ordered_list"):
            content_parts.append(_extract_list_content(child))

    return SemanticNode(
        node_type="list_item",
        content="\n".join(content_parts),
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        metadata={
            "chunk_type": "list",
            "heading_context": context,
        },
    )


def _extract_list_content(node: SemanticNode) -> str:
    """Extract content from a list (bullet or ordered)."""
    lines: list[str] = []

    for child in node.children:
        if child.node_type != "list_item":
            continue

        # Extract marker and content in a single pass
        marker = ""
        item_parts: list[str] = []

        for subchild in child.children:
            if "marker" in subchild.node_type:
                marker = subchild.content
            elif subchild.node_type == "paragraph":
                item_parts.append(subchild.content)
            elif "list" in subchild.node_type:
                item_parts.append(_extract_list_content(subchild))

        lines.append(f"{marker} {' '.join(item_parts)}")

    return "\n".join(lines)


def _wrap_with_context(node: SemanticNode, context: list[dict]) -> SemanticNode:
    """Wrap content with heading context if available."""
    if not context:
        return node

    # Add heading context to content
    context_text = "\n".join(
        "#" * h["level"] + " " + h["text"]
        for h in context
    )

    wrapped_content = f"{context_text}\n\n{node.content}"

    return SemanticNode(
        node_type=node.node_type,
        content=wrapped_content,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        children=node.children,
        metadata={
            **node.metadata,
            "heading_context": context,
        },
    )


def merge_to_target_size(
    nodes: list[SemanticNode],
    target_size: int,
    overlap: int,
    min_chunk_size: int = 100,
) -> list[str]:
    """Merge semantic nodes into chunks of approximately target_size.

    This function intelligently merges nodes while respecting semantic
    boundaries and maintaining context through overlap.

    Args:
        nodes: List of semantic nodes
        target_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size (discard smaller chunks)

    Returns:
        List of merged chunk texts
    """
    if not nodes:
        return []

    use_overlap = overlap > 0
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0
    last_chunk_context: list[dict] | None = None

    for node in nodes:
        node_text = node.content
        node_size = len(node_text)

        # Skip very small nodes that don't meet minimum
        if node_size < min_chunk_size and node.node_type not in ("heading", "table"):
            continue

        # Check if adding this node would exceed target size
        separator_size = 2 if current_chunk else 0  # \n\n
        new_size = current_size + separator_size + node_size

        if new_size > target_size and current_chunk:
            # Save current chunk
            chunks.append("\n\n".join(current_chunk))

            # Prepare overlap for next chunk
            if use_overlap:
                last_chunk_context = _extract_context_from_chunk(current_chunk[-1])

            # Start new chunk with overlap if available
            current_chunk = []
            current_size = 0

            if use_overlap and last_chunk_context:
                overlap_text = _build_overlap_text(last_chunk_context)
                if len(overlap_text) < overlap:
                    current_chunk.append(overlap_text)
                    current_size = len(overlap_text)

        # Add node to current chunk
        current_chunk.append(node_text)
        if len(current_chunk) > 1:
            current_size += separator_size + node_size
        else:
            current_size = node_size

    # Add final chunk
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        if len(chunk_text) >= min_chunk_size:
            chunks.append(chunk_text)

    # If no chunks were created, return original text
    if not chunks and nodes:
        full_text = "\n\n".join(n.content for n in nodes)
        if full_text:
            chunks.append(full_text)

    return chunks


def _extract_context_from_chunk(chunk_text: str) -> list[dict]:
    """Extract heading context from a chunk."""
    context: list[dict] = []
    for line in chunk_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            if text:
                context.append({"level": level, "text": text})
    return context


def _build_overlap_text(context: list[dict]) -> str:
    """Build overlap text from heading context."""
    if not context:
        return ""
    return "\n".join(
        "#" * h["level"] + " " + h["text"]
        for h in context
    )


def tree_sitter_chunk_document(document: Document, config: ChunkingConfig) -> list[Chunk]:
    """Create intelligent chunks from a Markdown document using tree-sitter.

    Args:
        document: Document to chunk (should be Markdown type)
        config: Chunking configuration

    Returns:
        List of Chunk objects
    """
    # Parse the document into a syntax tree
    tree = parse_markdown_syntax_tree(document.content)

    if tree is None:
        logger.info(
            "tree_sitter_parsing_failed_fallback",
            document_id=str(document.id),
        )
        return []

    # Extract semantic nodes
    semantic_nodes = extract_semantic_nodes(tree)

    if not semantic_nodes:
        logger.warning(
            "no_semantic_nodes_extracted",
            document_id=str(document.id),
        )
        return []

    # Merge nodes into target-sized chunks
    merged_texts = merge_to_target_size(
        semantic_nodes,
        config.chunk_size,
        config.chunk_overlap,
        config.min_chunk_size,
    )

    # Create Chunk objects
    chunks: list[Chunk] = []
    for idx, text in enumerate(merged_texts):
        # Find position in original document
        start_char = _find_position(document.content, text)
        end_char = min(start_char + len(text), len(document.content))
        if end_char <= start_char:
            end_char = min(start_char + 1, len(document.content))

        # Determine chunk type from metadata
        chunk_type = "content"
        if text.strip().startswith("|"):
            chunk_type = "table"
        elif "```" in text:
            chunk_type = "code"
        elif text.strip().startswith(("-", "*", "+")) or _is_ordered_list(text):
            chunk_type = "list"
        elif text.strip().startswith(">"):
            chunk_type = "blockquote"
        elif text.strip().startswith("#"):
            chunk_type = "heading"

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
        "tree_sitter_document_chunked",
        document_id=str(document.id),
        semantic_nodes=len(semantic_nodes),
        final_chunks=len(chunks),
        avg_chunk_size=sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0,
    )

    return chunks


def _find_position(doc_content: str, chunk_text: str) -> int:
    """Find the position of chunk_text in doc_content."""
    # Try exact match first
    pos = doc_content.find(chunk_text)
    if pos != -1:
        return pos

    # Try first 50 chars as anchor
    anchor = chunk_text[:50]
    pos = doc_content.find(anchor)
    if pos != -1:
        return pos

    # Fallback: estimate position
    return 0


def _is_ordered_list(text: str) -> bool:
    """Check if text is an ordered list."""
    first_line = text.strip().split("\n", 1)[0].strip()
    return bool(re.match(r"^\d+\.\s+", first_line))
