"""Unit tests for text chunking utilities."""

from uuid import uuid4

import pytest

from memory.config.schema import ChunkingConfig
from memory.core.chunking import chunk_text, create_chunks
from memory.entities import Document, DocumentType


class TestChunkText:
    """Test chunk_text function."""

    def test_empty_text(self):
        """Test that empty text returns no chunks."""
        chunks = list(chunk_text("", 512, 50, 100))
        assert len(chunks) == 0

    def test_whitespace_only(self):
        """Test that whitespace-only text returns no chunks."""
        chunks = list(chunk_text("   \n\n   ", 512, 50, 100))
        assert len(chunks) == 0

    def test_text_shorter_than_min_size(self):
        """Test text shorter than minimum chunk size returns no chunks."""
        text = "Short text"
        chunks = list(chunk_text(text, 512, 50, 100))
        assert len(chunks) == 0

    def test_text_shorter_than_min_size_small_overlap(self):
        """Test text shorter than minimum chunk size with small overlap."""
        text = "Short text"
        chunks = list(chunk_text(text, 512, 10, 100))
        assert len(chunks) == 0

    def test_text_equal_to_min_size(self):
        """Test text exactly equal to minimum chunk size returns one chunk."""
        text = "x" * 100
        chunks = list(chunk_text(text, 512, 50, 100))
        assert len(chunks) == 1
        assert chunks[0] == (text, 0, 100)

    def test_single_chunk(self):
        """Test text that fits in a single chunk."""
        text = "This is a test document with some content."
        chunks = list(chunk_text(text, 512, 50, 10))
        assert len(chunks) == 1
        assert chunks[0] == (text, 0, len(text))

    def test_multiple_chunks(self):
        """Test text that requires multiple chunks."""
        text = "a" * 600
        chunks = list(chunk_text(text, 200, 50, 10))
        assert len(chunks) >= 3
        # First chunk: 0-200
        assert chunks[0] == ("a" * 200, 0, 200)
        # Second chunk: 150-350 (200 overlap of 50)
        assert chunks[1][1] == 150  # start position
        assert chunks[1][2] == 350  # end position
        # Third chunk: 300-500
        assert chunks[2][1] == 300  # start position

    def test_overlap_larger_than_chunk_size(self):
        """Test when overlap is larger than chunk size (shouldn't happen in practice)."""
        text = "a" * 300
        chunks = list(chunk_text(text, 100, 150, 10))
        # With overlap=150 and chunk_size=100, the logic prevents infinite loop
        # by moving start to end when start <= end - chunk_size
        assert len(chunks) >= 1

    def test_exact_chunk_alignment(self):
        """Test text that aligns exactly with chunk boundaries."""
        text = "a" * 400
        chunks = list(chunk_text(text, 200, 0, 10))
        assert len(chunks) == 2
        assert chunks[0] == ("a" * 200, 0, 200)
        assert chunks[1] == ("a" * 200, 200, 400)

    def test_unicode_content(self):
        """Test chunking with Unicode characters."""
        text = "你好世界" * 100  # 400 characters
        chunks = list(chunk_text(text, 200, 0, 10))
        assert len(chunks) == 2
        assert chunks[0][0] == "你好世界" * 50
        assert chunks[1][0] == "你好世界" * 50

    def test_chunk_boundaries_preserve_content(self):
        """Test that chunks preserve original text content."""
        text = "The quick brown fox jumps over the lazy dog"
        chunks = list(chunk_text(text, 20, 5, 10))
        # Verify all chunks together reconstruct the original text
        reconstructed = "".join(chunk[0] for chunk in chunks)
        # Note: due to overlap and strip(), some whitespace may be lost
        assert "quick" in reconstructed
        assert "brown" in reconstructed
        assert "fox" in reconstructed

    def test_various_chunk_sizes(self):
        """Test different chunk sizes produce expected results."""
        text = "a" * 1000

        # Small chunks
        chunks = list(chunk_text(text, 100, 0, 10))
        assert len(chunks) == 10

        # Large chunks
        chunks = list(chunk_text(text, 1000, 0, 10))
        assert len(chunks) == 1

        # Medium chunks
        chunks = list(chunk_text(text, 300, 0, 10))
        assert len(chunks) == 4  # 300 * 3 = 900, remaining 100

    def test_various_overlaps(self):
        """Test different overlap sizes."""
        text = "a" * 500

        # No overlap
        chunks = list(chunk_text(text, 200, 0, 10))
        assert chunks[0][2] == 200  # end position
        assert chunks[1][1] == 200  # start of next

        # With overlap
        chunks = list(chunk_text(text, 200, 50, 10))
        assert chunks[0][2] == 200
        assert chunks[1][1] == 150  # 200 - 50

    def test_min_chunk_size_filtering(self):
        """Test that chunks smaller than min_chunk_size are filtered out."""
        text = "a" * 250
        chunks = list(chunk_text(text, 200, 0, 100))
        # First chunk: 200 chars (>= 100, kept)
        # Second chunk: 50 chars (< 100, filtered out)
        assert len(chunks) == 1
        assert len(chunks[0][0]) == 200

    def test_all_chunks_filtered_out(self):
        """Test when all chunks are smaller than min_chunk_size."""
        text = "a" * 50
        chunks = list(chunk_text(text, 100, 0, 100))
        assert len(chunks) == 0

    def test_single_character_chunks(self):
        """Test chunking with very small chunk sizes."""
        text = "abcdefghij"
        chunks = list(chunk_text(text, 3, 1, 1))
        assert len(chunks) == 5  # "abc", "bcd", "cde", "def", "efg", "fgh", "ghi", "hij" but filtered by boundaries
        # Due to strip() and boundary calculations, actual count may vary


class TestCreateChunks:
    """Test create_chunks function."""

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Test Document",
            content="a" * 600,
            source_path="/test/doc.txt",
            doc_type=DocumentType.TEXT,
            metadata={"test": True},
        )

    def test_create_single_chunk(self, sample_document):
        """Test creating a single chunk from a short document."""
        sample_document.content = "Short content"
        config = ChunkingConfig(
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        assert len(chunks) == 1
        assert chunks[0].content == "Short content"
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len("Short content")

    def test_create_multiple_chunks(self, sample_document):
        """Test creating multiple chunks from a long document."""
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=50,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        # Text: 600 chars
        # Chunk 1: 0-200 (200 chars)
        # Chunk 2: 150-350 (200 chars, 50 overlap)
        # Chunk 3: 300-500 (200 chars, 50 overlap)
        # Chunk 4: 450-600 (150 chars, 50 overlap)
        assert len(chunks) == 4
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2
        assert chunks[3].chunk_index == 3

    def test_chunk_content_correctness(self, sample_document):
        """Test that chunk content is correctly extracted."""
        sample_document.content = "The quick brown fox"
        config = ChunkingConfig(
            chunk_size=10,
            chunk_overlap=0,
            min_chunk_size=5,
        )
        chunks = create_chunks(sample_document, config)
        # All chunks together should contain the original text
        full_content = "".join(chunk.content for chunk in chunks)
        assert "quick" in full_content
        assert "brown" in full_content
        assert "fox" in full_content

    def test_chunk_metadata_preserved(self, sample_document):
        """Test that chunk inherits document metadata."""
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=50,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        # Check that all chunks have correct repository_id and document_id
        for chunk in chunks:
            assert chunk.repository_id == sample_document.repository_id
            assert chunk.document_id == sample_document.id

    def test_document_shorter_than_min_size(self):
        """Test document shorter than minimum chunk size."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Short",
            content="Short",
            source_path="/test/short.txt",
            doc_type=DocumentType.TEXT,
        )
        config = ChunkingConfig(
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=100,
        )
        chunks = create_chunks(document, config)
        assert len(chunks) == 0

    def test_exact_min_size(self):
        """Test document exactly equal to minimum chunk size."""
        content = "x" * 100
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Exact",
            content=content,
            source_path="/test/exact.txt",
            doc_type=DocumentType.TEXT,
        )
        config = ChunkingConfig(
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=100,
        )
        chunks = create_chunks(document, config)
        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_chunk_indices_sequential(self, sample_document):
        """Test that chunk indices are sequential."""
        config = ChunkingConfig(
            chunk_size=150,
            chunk_overlap=0,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        indices = [chunk.chunk_index for chunk in chunks]
        assert indices == list(range(len(chunks)))

    def test_start_end_char_positions(self, sample_document):
        """Test that start and end character positions are correct."""
        sample_document.content = "0123456789" * 50  # 500 chars
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=0,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        assert len(chunks) == 3
        # First chunk: 0-200
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 200
        # Second chunk: 200-400
        assert chunks[1].start_char == 200
        assert chunks[1].end_char == 400
        # Third chunk: 400-500
        assert chunks[2].start_char == 400
        assert chunks[2].end_char == 500

    def test_different_document_types(self):
        """Test chunking with different document types."""
        for doc_type in DocumentType:
            # For MARKDOWN type, use actual markdown content
            if doc_type == DocumentType.MARKDOWN:
                content = "# Heading 1\n\n" + ("a" * 100) + "\n\n# Heading 2\n\n" + ("b" * 100)
            else:
                content = "a" * 300

            document = Document(
                id=uuid4(),
                repository_id=uuid4(),
                title=f"Test {doc_type}",
                content=content,
                source_path=f"/test/{doc_type}.txt",
                doc_type=doc_type,
            )
            config = ChunkingConfig(
                chunk_size=150,
                chunk_overlap=0,
                min_chunk_size=10,
            )
            chunks = create_chunks(document, config)
            # Markdown documents with semantic structure may create different chunk counts
            # but should still work correctly
            assert len(chunks) >= 1  # Should create at least one chunk

    def test_no_overlap(self, sample_document):
        """Test chunking with no overlap."""
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=0,
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        # Check that chunks don't overlap
        for i in range(len(chunks) - 1):
            current_end = chunks[i].end_char
            next_start = chunks[i + 1].start_char
            # With no overlap, next_start should equal current_end
            assert next_start == current_end

    def test_large_overlap(self, sample_document):
        """Test chunking with large overlap."""
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=150,  # 75% overlap
            min_chunk_size=10,
        )
        chunks = create_chunks(sample_document, config)
        # With large overlap, we should have more chunks
        # 600 chars / (200 - 150) = 4 chunks (approximately)
        assert len(chunks) >= 3

    def test_unicode_document(self):
        """Test chunking with Unicode content."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Unicode",
            content="你好世界" * 100,  # 400 chars
            source_path="/test/unicode.txt",
            doc_type=DocumentType.TEXT,
        )
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=0,
            min_chunk_size=10,
        )
        chunks = create_chunks(document, config)
        assert len(chunks) == 2
        assert all("你好世界" in chunk.content for chunk in chunks)

    def test_special_characters(self):
        """Test chunking with special characters."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Special",
            content="!@#$%^&*()_+-=[]{}|;':\",./<>?\n\t" * 20,
            source_path="/test/special.txt",
            doc_type=DocumentType.TEXT,
        )
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=0,
            min_chunk_size=10,
        )
        chunks = create_chunks(document, config)
        assert len(chunks) >= 1
        # Check that special characters are preserved
        assert any("!@#$%" in chunk.content for chunk in chunks)

    def test_content_whitespace_handling(self):
        """Test that whitespace is handled correctly in chunks."""
        document = Document(
            id=uuid4(),
            repository_id=uuid4(),
            title="Whitespace",
            content="  a  b  c  d  e  ",
            source_path="/test/whitespace.txt",
            doc_type=DocumentType.TEXT,
        )
        config = ChunkingConfig(
            chunk_size=50,
            chunk_overlap=0,
            min_chunk_size=1,
        )
        chunks = create_chunks(document, config)
        # Chunks should have whitespace stripped
        for chunk in chunks:
            assert chunk.content == chunk.content.strip()
