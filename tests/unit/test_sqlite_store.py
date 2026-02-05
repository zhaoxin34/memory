"""Unit tests for SQLite storage implementations."""

import pytest
import tempfile
import os
from uuid import uuid4

from memory.storage.sqlite import SQLiteMetadataStore
from memory.storage.base import StorageConfig
from memory.core.models import Document, Repository, Chunk, DocumentType


@pytest.mark.asyncio
class TestSQLiteMetadataStore:
    """Test SQLiteMetadataStore functionality."""

    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database file."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        yield db_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def store(self, temp_db):
        """Create a SQLiteMetadataStore instance for testing."""
        store = SQLiteMetadataStore(
            StorageConfig(
                storage_type="sqlite",
                connection_string=f"sqlite:///{temp_db}",
                collection_name="test",
            )
        )
        await store.initialize()
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_delete_by_repository_empty(self, store):
        """Test deleting from an empty repository."""
        repo_id = uuid4()
        count = await store.delete_by_repository(repo_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_by_repository_with_docs(self, store):
        """Test deleting documents from a repository."""
        # Create a repository
        repository = Repository(
            name="test-repo",
            description="Test repository",
        )
        await store.add_repository(repository)

        # Create test documents
        doc1 = Document(
            repository_id=repository.id,
            source_path="/path/to/doc1.txt",
            doc_type=DocumentType.TEXT,
            title="Document 1",
            content="Content of document 1",
        )
        doc2 = Document(
            repository_id=repository.id,
            source_path="/path/to/doc2.txt",
            doc_type=DocumentType.TEXT,
            title="Document 2",
            content="Content of document 2",
        )

        await store.add_document(doc1)
        await store.add_document(doc2)

        # Create test chunks
        chunk1 = Chunk(
            repository_id=repository.id,
            document_id=doc1.id,
            content="Chunk 1 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )
        chunk2 = Chunk(
            repository_id=repository.id,
            document_id=doc2.id,
            content="Chunk 2 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )

        await store.add_chunk(chunk1)
        await store.add_chunk(chunk2)

        # Verify documents exist
        docs = await store.list_documents(repository_id=repository.id)
        assert len(docs) == 2

        # Delete repository contents
        count = await store.delete_by_repository(repository.id)
        assert count == 2

        # Verify documents are deleted
        docs = await store.list_documents(repository_id=repository.id)
        assert len(docs) == 0

        # Verify chunks are deleted via CASCADE
        retrieved_chunk1 = await store.get_chunk(chunk1.id)
        retrieved_chunk2 = await store.get_chunk(chunk2.id)
        assert retrieved_chunk1 is None
        assert retrieved_chunk2 is None

        # Verify repository still exists
        repo = await store.get_repository(repository.id)
        assert repo is not None
        assert repo.name == "test-repo"

    @pytest.mark.asyncio
    async def test_delete_by_repository_multiple_repos(self, store):
        """Test deleting from one repository doesn't affect others."""
        # Create two repositories
        repo1 = Repository(
            name="test-repo-1",
            description="Test repository 1",
        )
        repo2 = Repository(
            name="test-repo-2",
            description="Test repository 2",
        )
        await store.add_repository(repo1)
        await store.add_repository(repo2)

        # Add documents to both repositories
        doc1 = Document(
            repository_id=repo1.id,
            source_path="/path/to/doc1.txt",
            doc_type=DocumentType.TEXT,
            title="Document 1",
            content="Content of document 1",
        )
        doc2 = Document(
            repository_id=repo2.id,
            source_path="/path/to/doc2.txt",
            doc_type=DocumentType.TEXT,
            title="Document 2",
            content="Content of document 2",
        )

        await store.add_document(doc1)
        await store.add_document(doc2)

        # Delete from repo1
        count = await store.delete_by_repository(repo1.id)
        assert count == 1

        # Verify repo1 is empty
        docs1 = await store.list_documents(repository_id=repo1.id)
        assert len(docs1) == 0

        # Verify repo2 still has documents
        docs2 = await store.list_documents(repository_id=repo2.id)
        assert len(docs2) == 1
        assert docs2[0].title == "Document 2"

    @pytest.mark.asyncio
    async def test_delete_by_repository_cascade(self, store):
        """Test that CASCADE DELETE works correctly."""
        # Create a repository
        repository = Repository(
            name="test-repo",
            description="Test repository",
        )
        await store.add_repository(repository)

        # Create a document with multiple chunks
        doc = Document(
            repository_id=repository.id,
            source_path="/path/to/doc.txt",
            doc_type=DocumentType.TEXT,
            title="Test Document",
            content="Content of test document",
        )
        await store.add_document(doc)

        # Create multiple chunks
        chunks = [
            Chunk(
                repository_id=repository.id,
                document_id=doc.id,
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=i * 10,
                end_char=(i + 1) * 10,
            )
            for i in range(3)
        ]

        for chunk in chunks:
            await store.add_chunk(chunk)

        # Verify chunks exist
        for chunk in chunks:
            retrieved = await store.get_chunk(chunk.id)
            assert retrieved is not None

        # Delete repository contents
        count = await store.delete_by_repository(repository.id)
        assert count == 1

        # Verify all chunks are deleted
        for chunk in chunks:
            retrieved = await store.get_chunk(chunk.id)
            assert retrieved is None

        # Verify document is deleted
        retrieved_doc = await store.get_document(doc.id)
        assert retrieved_doc is None
