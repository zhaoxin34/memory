"""Tests for core domain models."""

from datetime import datetime
from uuid import UUID

import pytest

from memory.core.models import Chunk, Document, DocumentType, Embedding, SearchResult


def test_document_creation():
    """Test creating a valid document."""
    doc = Document(
        source_path="/path/to/doc.md",
        doc_type=DocumentType.MARKDOWN,
        title="Test Document",
        content="This is test content.",
    )

    assert isinstance(doc.id, UUID)
    assert doc.source_path == "/path/to/doc.md"
    assert doc.doc_type == DocumentType.MARKDOWN
    assert doc.title == "Test Document"
    assert doc.content == "This is test content."
    assert isinstance(doc.created_at, datetime)


def test_document_empty_content_fails():
    """Test that empty content raises validation error."""
    with pytest.raises(ValueError, match="Document content cannot be empty"):
        Document(
            source_path="/path/to/doc.md",
            content="",
        )


def test_chunk_creation():
    """Test creating a valid chunk."""
    doc_id = UUID("12345678-1234-5678-1234-567812345678")
    chunk = Chunk(
        document_id=doc_id,
        content="This is a chunk.",
        chunk_index=0,
        start_char=0,
        end_char=16,
    )

    assert isinstance(chunk.id, UUID)
    assert chunk.document_id == doc_id
    assert chunk.content == "This is a chunk."
    assert chunk.chunk_index == 0
    assert chunk.start_char == 0
    assert chunk.end_char == 16


def test_chunk_invalid_range_fails():
    """Test that invalid character range raises validation error."""
    doc_id = UUID("12345678-1234-5678-1234-567812345678")
    with pytest.raises(ValueError, match="end_char must be greater than start_char"):
        Chunk(
            document_id=doc_id,
            content="Test",
            chunk_index=0,
            start_char=10,
            end_char=5,  # Invalid: end before start
        )


def test_embedding_creation():
    """Test creating a valid embedding."""
    chunk_id = UUID("12345678-1234-5678-1234-567812345678")
    vector = [0.1, 0.2, 0.3, 0.4, 0.5]

    embedding = Embedding(
        chunk_id=chunk_id,
        vector=vector,
        model="test-model",
        dimension=5,
    )

    assert embedding.chunk_id == chunk_id
    assert embedding.vector == vector
    assert embedding.model == "test-model"
    assert embedding.dimension == 5


def test_embedding_dimension_mismatch_fails():
    """Test that dimension mismatch raises validation error."""
    chunk_id = UUID("12345678-1234-5678-1234-567812345678")
    with pytest.raises(ValueError, match="Dimension .* does not match vector length"):
        Embedding(
            chunk_id=chunk_id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=5,  # Mismatch: vector has 3 elements
        )


def test_search_result_creation():
    """Test creating a search result."""
    doc = Document(
        source_path="/path/to/doc.md",
        content="Test content",
    )
    chunk = Chunk(
        document_id=doc.id,
        content="Test chunk",
        chunk_index=0,
        start_char=0,
        end_char=10,
    )

    result = SearchResult(
        chunk=chunk,
        score=0.95,
        document=doc,
    )

    assert result.chunk == chunk
    assert result.score == 0.95
    assert result.document == doc
