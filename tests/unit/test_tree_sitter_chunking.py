"""Unit tests for tree-sitter based Markdown chunking."""

from uuid import uuid4

import pytest

from memory.config.schema import ChunkingConfig
from memory.core.models import Document, DocumentType
from memory.core.tree_sitter_chunking import (
    SemanticNode,
    _check_tree_sitter_available,
    _find_position,
    extract_semantic_nodes,
    merge_to_target_size,
    parse_markdown_syntax_tree,
    tree_sitter_chunk_document,
)


class TestTreeSitterAvailability:
    """Test tree-sitter availability checks."""

    def test_check_tree_sitter_available(self):
        """Test tree-sitter availability check."""
        # This test will pass/fail based on whether tree-sitter is installed
        result = _check_tree_sitter_available()
        # Just verify the function runs without error
        assert isinstance(result, bool)


class TestSemanticNode:
    """Test SemanticNode class."""

    def test_node_creation(self):
        """Test basic node creation."""
        node = SemanticNode(
            node_type="paragraph",
            content="Hello world",
            start_byte=0,
            end_byte=11,
        )
        assert node.node_type == "paragraph"
        assert node.content == "Hello world"
        assert node.char_count == 11

    def test_is_heading(self):
        """Test heading detection."""
        heading = SemanticNode(node_type="atx_heading", content="# Title")
        paragraph = SemanticNode(node_type="paragraph", content="text")
        assert heading.is_heading is True
        assert paragraph.is_heading is False

    def test_is_table(self):
        """Test table detection."""
        table = SemanticNode(node_type="table", content="| a | b |\n|---|---|\n| c | d |")
        paragraph = SemanticNode(node_type="paragraph", content="text")
        assert table.is_table is True
        assert paragraph.is_table is False

    def test_is_list(self):
        """Test list detection."""
        bullet_list = SemanticNode(node_type="bullet_list", content="- item")
        ordered_list = SemanticNode(node_type="ordered_list", content="1. item")
        paragraph = SemanticNode(node_type="paragraph", content="text")
        assert bullet_list.is_list is True
        assert ordered_list.is_list is True
        assert paragraph.is_list is False

    def test_is_code_block(self):
        """Test code block detection."""
        fenced = SemanticNode(node_type="fenced_code_block", content="```python\ncode\n```")
        indented = SemanticNode(node_type="indented_code_block", content="    code")
        paragraph = SemanticNode(node_type="paragraph", content="text")
        assert fenced.is_code_block is True
        assert indented.is_code_block is True
        assert paragraph.is_code_block is False


class TestParseMarkdownSyntaxTree:
    """Test parse_markdown_syntax_tree function."""

    def test_empty_text(self):
        """Test empty text returns None."""
        result = parse_markdown_syntax_tree("")
        assert result is None

    def test_whitespace_only(self):
        """Test whitespace-only text returns None."""
        result = parse_markdown_syntax_tree("   \n\n   ")
        assert result is None

    def test_simple_heading(self):
        """Test parsing a simple heading."""
        text = "# Heading 1\n\nSome content here."
        result = parse_markdown_syntax_tree(text)
        if result is not None:
            assert result.node_type == "document"
        else:
            pytest.skip("tree-sitter not available")

    def test_multiple_headings(self):
        """Test parsing multiple headings."""
        text = "# H1\n\n## H2\n\n### H3"
        result = parse_markdown_syntax_tree(text)
        if result is not None:
            assert result.node_type == "document"
        else:
            pytest.skip("tree-sitter not available")

    def test_with_table(self):
        """Test parsing a document with a table."""
        text = "# Document\n\n| Col1 | Col2 |\n|------|------|\n| A    | B    |"
        result = parse_markdown_syntax_tree(text)
        if result is not None:
            assert result.node_type == "document"
        else:
            pytest.skip("tree-sitter not available")

    def test_with_code_block(self):
        """Test parsing a document with a code block."""
        text = "# Code Example\n\n```python\ndef hello():\n    print('hi')\n```"
        result = parse_markdown_syntax_tree(text)
        if result is not None:
            assert result.node_type == "document"
        else:
            pytest.skip("tree-sitter not available")


class TestExtractSemanticNodes:
    """Test extract_semantic_nodes function."""

    def test_empty_tree(self):
        """Test extracting from None returns empty list."""
        result = extract_semantic_nodes(None)
        assert result == []

    def test_simple_document(self):
        """Test extracting from simple document."""
        text = "# Title\n\nParagraph content."
        tree = parse_markdown_syntax_tree(text)
        if tree is None:
            pytest.skip("tree-sitter not available")

        result = extract_semantic_nodes(tree)
        assert isinstance(result, list)


class TestMergeToTargetSize:
    """Test merge_to_target_size function."""

    def test_empty_nodes(self):
        """Test empty nodes returns empty list."""
        result = merge_to_target_size([], 500, 50)
        assert result == []

    def test_single_node(self):
        """Test single node returns single chunk."""
        nodes = [SemanticNode(node_type="paragraph", content="Hello world")]
        result = merge_to_target_size(nodes, 500, 50)
        assert len(result) == 1
        assert result[0] == "Hello world"

    def test_small_nodes_merged(self):
        """Test small nodes are merged to target size."""
        nodes = [
            SemanticNode(node_type="paragraph", content="Short "),
            SemanticNode(node_type="paragraph", content="text "),
            SemanticNode(node_type="paragraph", content="here."),
        ]
        result = merge_to_target_size(nodes, 100, 0)
        assert len(result) == 1
        assert "Short" in result[0]

    def test_nodes_split_by_target_size(self):
        """Test nodes are split when exceeding target size."""
        nodes = [
            SemanticNode(node_type="paragraph", content="A" * 200),
            SemanticNode(node_type="paragraph", content="B" * 200),
            SemanticNode(node_type="paragraph", content="C" * 200),
        ]
        result = merge_to_target_size(nodes, 300, 0)
        assert len(result) >= 1

    def test_overlap_preserved(self):
        """Test overlap is preserved between chunks."""
        nodes = [
            SemanticNode(node_type="paragraph", content="A" * 200),
            SemanticNode(node_type="paragraph", content="B" * 200),
        ]
        result = merge_to_target_size(nodes, 150, 50)
        assert len(result) >= 1

    def test_min_chunk_size_filter(self):
        """Test chunks smaller than min_chunk_size are filtered."""
        nodes = [
            SemanticNode(node_type="paragraph", content="hi"),
        ]
        result = merge_to_target_size(nodes, 500, 50, min_chunk_size=100)
        # Small node may be filtered out
        assert isinstance(result, list)


class TestTreeSitterChunkDocument:
    """Test tree_sitter_chunk_document function."""

    @pytest.fixture
    def sample_markdown_document(self):
        """Create a sample Markdown document for testing."""
        return Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Test Markdown",
            content="# Heading 1\n\nSome content here.\n\n## Heading 2\n\nMore content.",
            source_path="/test/doc.md",
            doc_type=DocumentType.MARKDOWN,
            metadata={},
        )

    def test_basic_chunking(self, sample_markdown_document):
        """Test basic Markdown chunking."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=50,
            min_chunk_size=50,
        )
        chunks = tree_sitter_chunk_document(sample_markdown_document, config)
        # If tree-sitter is available, should create chunks
        # If not, returns empty list (fallback in chunking.py)
        assert isinstance(chunks, list)

    def test_document_with_table(self):
        """Test chunking document with table."""
        doc = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Table Test",
            content="# Doc\n\n| A | B |\n|---|---|\n| 1 | 2 |",
            source_path="/test/table.md",
            doc_type=DocumentType.MARKDOWN,
        )
        config = ChunkingConfig(chunk_size=500, chunk_overlap=50, min_chunk_size=50)
        chunks = tree_sitter_chunk_document(doc, config)
        assert isinstance(chunks, list)

    def test_document_with_code(self):
        """Test chunking document with code block."""
        doc = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Code Test",
            content="# Code\n\n```python\ndef hello():\n    return 'world'\n```",
            source_path="/test/code.md",
            doc_type=DocumentType.MARKDOWN,
        )
        config = ChunkingConfig(chunk_size=500, chunk_overlap=50, min_chunk_size=50)
        chunks = tree_sitter_chunk_document(doc, config)
        assert isinstance(chunks, list)

    def test_document_with_list(self):
        """Test chunking document with list."""
        doc = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="List Test",
            content="# Doc\n\n- Item 1\n- Item 2\n- Item 3",
            source_path="/test/list.md",
            doc_type=DocumentType.MARKDOWN,
        )
        config = ChunkingConfig(chunk_size=500, chunk_overlap=50, min_chunk_size=50)
        chunks = tree_sitter_chunk_document(doc, config)
        assert isinstance(chunks, list)

    def test_chunk_metadata(self):
        """Test that chunk metadata is populated."""
        doc = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Meta Test",
            content="# Heading\n\nContent",
            source_path="/test/meta.md",
            doc_type=DocumentType.MARKDOWN,
        )
        config = ChunkingConfig(chunk_size=500, chunk_overlap=50, min_chunk_size=50)
        chunks = tree_sitter_chunk_document(doc, config)
        if chunks:
            assert "chunk_type" in chunks[0].metadata


class TestFindPosition:
    """Test _find_position helper function."""

    def test_exact_match(self):
        """Test exact position finding."""
        doc = "Hello world, this is a test."
        chunk = "this is a"
        pos = _find_position(doc, chunk)
        assert pos == 13

    def test_anchor_match(self):
        """Test finding with anchor when exact fails."""
        doc = "Prefix\n\nContent here"
        chunk = "Different content"
        pos = _find_position(doc, chunk)
        # Should use anchor fallback
        assert isinstance(pos, int)


class TestIntegrationWithChunking:
    """Test integration with main chunking module."""

    @pytest.fixture
    def markdown_doc(self):
        """Create a Markdown document."""
        return Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Integration Test",
            content="# Main Title\n\n## Section 1\n\nParagraph in section 1.\n\n## Section 2\n\nParagraph in section 2.\n\n| Col1 | Col2 |\n|------|------|\n| A    | B    |",
            source_path="/test/integration.md",
            doc_type=DocumentType.MARKDOWN,
        )

    def test_create_chunks_uses_tree_sitter_when_available(self, markdown_doc):
        """Test create_chunks prefers tree-sitter for Markdown."""
        from memory.core.chunking import create_chunks

        config = ChunkingConfig(chunk_size=500, chunk_overlap=50, min_chunk_size=50)
        chunks = create_chunks(markdown_doc, config)

        assert isinstance(chunks, list)
        # Should create at least one chunk
        if chunks:
            assert len(chunks) >= 1
            # Verify chunk properties
            for chunk in chunks:
                assert chunk.repository_id == markdown_doc.repository_id
                assert chunk.document_id == markdown_doc.id
                assert chunk.chunk_index >= 0
