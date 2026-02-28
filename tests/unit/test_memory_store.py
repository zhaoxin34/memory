"""Unit tests for InMemory storage implementations."""

from uuid import uuid4

import pytest

from memory.core.models import Chunk, Document, DocumentType, Embedding, Repository
from memory.storage.base import StorageConfig
from memory.storage.memory import InMemoryMetadataStore, InMemoryVectorStore


@pytest.mark.asyncio
class TestInMemoryMetadataStore:
    """Test InMemoryMetadataStore functionality."""

    @pytest.fixture
    async def store(self):
        """Create an InMemoryMetadataStore instance for testing."""
        store = InMemoryMetadataStore(
            StorageConfig(
                storage_type="memory",
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

        # Verify chunks are deleted
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
class TestInMemoryVectorStore:
    """Test InMemoryVectorStore functionality."""

    @pytest.fixture
    async def store(self):
        """Create an InMemoryVectorStore instance for testing."""
        store = InMemoryVectorStore(
            StorageConfig(
                storage_type="memory",
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
    async def test_delete_by_repository_with_embeddings(self, store):
        """Test deleting embeddings from a repository."""
        repo_id = uuid4()
        doc_id = uuid4()

        # Create test chunks with the repository
        chunk1 = Chunk(
            repository_id=repo_id,
            document_id=doc_id,
            content="Chunk 1 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )
        chunk2 = Chunk(
            repository_id=repo_id,
            document_id=doc_id,
            content="Chunk 2 content",
            chunk_index=1,
            start_char=0,
            end_char=15,
        )

        # Create embeddings
        embedding1 = Embedding(
            chunk_id=chunk1.id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )
        embedding2 = Embedding(
            chunk_id=chunk2.id,
            vector=[0.4, 0.5, 0.6],
            model="test-model",
            dimension=3,
        )

        # Add embeddings
        await store.add_embedding(embedding1, chunk1)
        await store.add_embedding(embedding2, chunk2)

        # Verify embeddings exist
        count = await store.count()
        assert count == 2

        # Delete repository embeddings
        deleted_count = await store.delete_by_repository(repo_id)
        assert deleted_count == 2

        # Verify embeddings are deleted
        count = await store.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_by_repository_multiple_repos(self, store):
        """Test deleting from one repository doesn't affect others."""
        repo1_id = uuid4()
        repo2_id = uuid4()
        doc_id = uuid4()

        # Create chunks for both repositories
        chunk1 = Chunk(
            repository_id=repo1_id,
            document_id=doc_id,
            content="Chunk 1 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )
        chunk2 = Chunk(
            repository_id=repo2_id,
            document_id=doc_id,
            content="Chunk 2 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )

        # Create embeddings
        embedding1 = Embedding(
            chunk_id=chunk1.id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )
        embedding2 = Embedding(
            chunk_id=chunk2.id,
            vector=[0.4, 0.5, 0.6],
            model="test-model",
            dimension=3,
        )

        # Add embeddings
        await store.add_embedding(embedding1, chunk1)
        await store.add_embedding(embedding2, chunk2)

        # Delete from repo1
        count = await store.delete_by_repository(repo1_id)
        assert count == 1

        # Verify repo1 is empty
        count = await store.count()
        assert count == 1

        # Verify repo2 still has embeddings
        count = await store.delete_by_repository(repo2_id)
        assert count == 1
