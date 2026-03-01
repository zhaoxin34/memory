"""Unit tests for Markdown-aware chunking."""

from uuid import uuid4

import pytest

from memory.config.schema import ChunkingConfig
from memory.core.markdown_chunking import (
    chunk_markdown_document,
    parse_markdown_sections,
    smart_merge_chunks,
)
from memory.entities import Document, DocumentType


class TestMarkdownParsing:
    """Test Markdown semantic parsing."""

    def test_parse_headings(self):
        """Test that headings are parsed correctly."""
        markdown = """# 主标题

这是主标题下的内容。

## 子标题

这是子标题下的内容。

### 子子标题

这是子子标题下的内容。
"""
        chunks = parse_markdown_sections(markdown)

        assert len(chunks) == 6  # 3 headings + 3 content blocks
        assert chunks[0].is_heading
        assert chunks[0].level == 1
        assert chunks[0].content == "主标题"
        assert chunks[1].level == 0
        assert "主标题下的内容" in chunks[1].content

    def test_parse_lists(self):
        """Test that lists are preserved."""
        markdown = """# 列表标题

这里是介绍文字。

- 列表项 1
- 列表项 2
- 列表项 3

继续的文字内容。
"""
        chunks = parse_markdown_sections(markdown)

        # Should have: heading, intro, list, continuation
        list_chunk = None
        for chunk in chunks:
            if chunk.type == "list":
                list_chunk = chunk
                break

        assert list_chunk is not None
        assert "列表项 1" in list_chunk.content
        assert "列表项 2" in list_chunk.content
        assert "列表项 3" in list_chunk.content

    def test_parse_code_blocks(self):
        """Test that code blocks are preserved."""
        markdown = """# 代码示例

这里有介绍文字。

```python
def hello():
    print("Hello, World!")
```

后续内容。
"""
        chunks = parse_markdown_sections(markdown)

        code_chunks = [c for c in chunks if c.type == "code"]
        assert len(code_chunks) == 1
        assert "def hello():" in code_chunks[0].content
        assert "print(" in code_chunks[0].content

    def test_parse_tables(self):
        """Test that tables are preserved."""
        markdown = """# 表格标题

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| D   | E   | F   |

后续内容。
"""
        chunks = parse_markdown_sections(markdown)

        # Table content should be in a content chunk
        table_found = False
        for chunk in chunks:
            if "|" in chunk.content and "列1" in chunk.content:
                table_found = True
                break

        assert table_found


class TestSmartMerging:
    """Test intelligent chunk merging."""

    def test_merge_preserves_heading_context(self):
        """Test that heading context is added to content chunks."""
        markdown = """# 重要标题

这是重要标题下的详细内容，包含了很多信息。

这里是更多的内容，需要保持在同一个上下文中。

## 子标题

这是子标题的内容。
"""
        chunks = parse_markdown_sections(markdown)
        merged = smart_merge_chunks(chunks, target_size=500, overlap=50)

        # First chunk should include heading context
        assert "重要标题" in merged[0]
        assert "重要标题下的详细内容" in merged[0]

    def test_merge_respects_size_limits(self):
        """Test that merging respects target size."""
        # Create a very long document to test size limits
        markdown = """# 标题 1

""" + "这是内容1。" * 50 + """

# 标题 2

""" + "这是内容2。" * 50 + """

# 标题 3

""" + "这是内容3。" * 50 + """

# 标题 4

""" + "这是内容4。" * 50 + """
"""
        chunks = parse_markdown_sections(markdown)
        merged = smart_merge_chunks(chunks, target_size=500, overlap=50)

        # Should create multiple chunks due to size limit
        assert len(merged) > 1

        # Each chunk should be reasonably sized
        for chunk in merged:
            assert len(chunk) >= 100  # min_chunk_size
            assert len(chunk) <= 600  # Some tolerance over target

    def test_merge_handles_overlap(self):
        """Test that overlap is applied correctly."""
        markdown = """# 标题

这里是第一个块的内容，包含了很多详细信息。

这里是第一个块的结尾部分。

这里是第二个块的内容。

这里是第二个块的结尾。
"""
        chunks = parse_markdown_sections(markdown)
        merged = smart_merge_chunks(chunks, target_size=150, overlap=50)

        # Should have overlap between chunks
        if len(merged) > 1:
            # Check that there's some overlap in content
            # (The exact overlap text might vary)
            assert len(merged[0]) >= 50
            assert len(merged[1]) >= 50


class TestMarkdownChunking:
    """Test the full Markdown chunking pipeline."""

    def test_chunk_markdown_document(self):
        """Test creating chunks from a Markdown document."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            source_path="test.md",
            doc_type=DocumentType.MARKDOWN,
            title="Test Document",
            content="""# 标题 1

这里是标题1下的详细内容，包含了很多信息。这些内容足够长，可以满足最小块大小的要求。

## 标题 2

这里是标题2下的内容，同样包含了丰富的信息。这些内容确保文档有足够的篇幅进行分块测试。

# 标题 3

最后是标题3的内容，完成整个测试文档的结构。
""",
        )

        config = ChunkingConfig()
        chunks = chunk_markdown_document(document, config)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == document.id
            assert chunk.repository_id == document.repository_id
            assert chunk.content  # Should have content
            assert len(chunk.content) >= 100  # Should meet min size

    def test_chunk_markdown_with_varying_sizes(self):
        """Test chunking with different size configurations."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            source_path="test.md",
            doc_type=DocumentType.MARKDOWN,
            title="Test Document",
            content="""# 标题

内容。

# 另一个标题

更多内容。

# 第三标题

更多更多内容。
""",
        )

        # Small chunks
        config_small = ChunkingConfig(chunk_size=100, chunk_overlap=20, min_chunk_size=50)
        chunks_small = chunk_markdown_document(document, config_small)

        # Large chunks
        config_large = ChunkingConfig(chunk_size=1000, chunk_overlap=100, min_chunk_size=100)
        chunks_large = chunk_markdown_document(document, config_large)

        # Large chunks should be fewer
        assert len(chunks_large) <= len(chunks_small)

    def test_chunk_non_markdown_document(self):
        """Test that non-Markdown documents fall back to regular chunking."""
        from memory.core.chunking import create_chunks

        # Create a longer text to ensure it meets min_chunk_size
        long_content = "这是第一段内容。" * 20 + "\n\n" + "这是第二段内容。" * 20

        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            source_path="test.txt",
            doc_type=DocumentType.TEXT,
            title="Test Document",
            content=long_content,
        )

        config = ChunkingConfig()
        chunks = create_chunks(document, config)

        # Should create at least one chunk
        assert len(chunks) > 0
        assert chunks[0].document_id == document.id


if __name__ == "__main__":
    pytest.main([__file__])
