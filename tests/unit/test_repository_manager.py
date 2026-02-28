"""Unit tests for RepositoryManager."""

from uuid import uuid4

import pytest

from memory.core.models import Document, DocumentType
from memory.core.repository import RepositoryManager, RepositoryNotFoundError
from memory.storage.base import StorageConfig
from memory.storage.memory import InMemoryMetadataStore, InMemoryVectorStore


@pytest.mark.asyncio
class TestRepositoryManager:
    """Test RepositoryManager functionality."""

    @pytest.fixture
    async def stores(self):
        """Create in-memory stores for testing."""
        metadata_store = InMemoryMetadataStore(
            StorageConfig(
                storage_type="memory",
                collection_name="test",
            )
        )
        vector_store = InMemoryVectorStore(
            StorageConfig(
                storage_type="memory",
                collection_name="test",
            )
        )
        await metadata_store.initialize()
        await vector_store.initialize()
        yield metadata_store, vector_store
        await metadata_store.close()
        await vector_store.close()

    @pytest.mark.asyncio
    async def test_clear_repository_not_found(self, stores):
        """Test clearing a non-existent repository raises error."""
        metadata_store, vector_store = stores
        repo_manager = RepositoryManager(metadata_store, vector_store)

        fake_id = uuid4()
        with pytest.raises(RepositoryNotFoundError) as exc_info:
            await repo_manager.clear_repository(fake_id)

        assert str(fake_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_clear_repository_happy_path(self, stores):
        """Test clearing a repository successfully."""
        metadata_store, vector_store = stores
        repo_manager = RepositoryManager(metadata_store, vector_store)

        # Create a repository
        repository = await repo_manager.create_repository(
            name="test-repo",
            description="Test repository",
        )

        # Add a document
        from memory.core.models import Chunk, Embedding

        doc = Document(
            repository_id=repository.id,
            source_path="/path/to/doc.txt",
            doc_type=DocumentType.TEXT,
            title="Test Document",
            content="Test content",
        )
        await metadata_store.add_document(doc)

        # Create a chunk
        chunk = Chunk(
            repository_id=repository.id,
            document_id=doc.id,
            content="Test chunk content",
            chunk_index=0,
            start_char=0,
            end_char=18,
        )
        await metadata_store.add_chunk(chunk)

        # Add an embedding
        embedding = Embedding(
            chunk_id=chunk.id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )
        await vector_store.add_embedding(embedding, chunk)

        # Verify document exists
        docs = await metadata_store.list_documents(repository_id=repository.id)
        assert len(docs) == 1

        # Verify embedding exists
        count = await vector_store.count()
        assert count == 1

        # Clear repository
        deleted_count = await repo_manager.clear_repository(repository.id)
        assert deleted_count == 1

        # Verify document is deleted
        docs = await metadata_store.list_documents(repository_id=repository.id)
        assert len(docs) == 0

        # Verify embedding is deleted
        count = await vector_store.count()
        assert count == 0

        # Verify repository still exists
        retrieved_repo = await repo_manager.get_repository(repository.id)
        assert retrieved_repo is not None
        assert retrieved_repo.name == "test-repo"

    @pytest.mark.asyncio
    async def test_clear_repository_empty(self, stores):
        """Test clearing an empty repository."""
        metadata_store, vector_store = stores
        repo_manager = RepositoryManager(metadata_store, vector_store)

        # Create a repository with no documents
        repository = await repo_manager.create_repository(
            name="empty-repo",
            description="Empty repository",
        )

        # Clear repository
        deleted_count = await repo_manager.clear_repository(repository.id)
        assert deleted_count == 0

        # Verify repository still exists
        retrieved_repo = await repo_manager.get_repository(repository.id)
        assert retrieved_repo is not None
        assert retrieved_repo.name == "empty-repo"

    @pytest.mark.asyncio
    async def test_clear_repository_multiple_docs(self, stores):
        """Test clearing a repository with multiple documents."""
        metadata_store, vector_store = stores
        repo_manager = RepositoryManager(metadata_store, vector_store)

        # Create a repository
        repository = await repo_manager.create_repository(
            name="multi-doc-repo",
            description="Repository with multiple documents",
        )

        # Add multiple documents
        from memory.core.models import Chunk, Embedding

        docs = [
            Document(
                repository_id=repository.id,
                source_path=f"/path/to/doc{i}.txt",
                doc_type=DocumentType.TEXT,
                title=f"Document {i}",
                content=f"Content of document {i}",
            )
            for i in range(1, 4)
        ]

        for i, doc in enumerate(docs, start=1):
            await metadata_store.add_document(doc)

            # Add a chunk and embedding for each document
            chunk = Chunk(
                repository_id=repository.id,
                document_id=doc.id,
                content=f"Chunk content for doc {i}",
                chunk_index=0,
                start_char=0,
                end_char=20,
            )
            await metadata_store.add_chunk(chunk)

            embedding = Embedding(
                chunk_id=chunk.id,
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                model="test-model",
                dimension=3,
            )
            await vector_store.add_embedding(embedding, chunk)

        # Verify documents exist
        docs = await metadata_store.list_documents(repository_id=repository.id)
        assert len(docs) == 3

        # Clear repository
        deleted_count = await repo_manager.clear_repository(repository.id)
        assert deleted_count == 3

        # Verify all documents are deleted
        docs = await metadata_store.list_documents(repository_id=repository.id)
        assert len(docs) == 0

        # Verify all embeddings are deleted
        count = await vector_store.count()
        assert count == 0

        # Verify repository still exists
        retrieved_repo = await repo_manager.get_repository(repository.id)
        assert retrieved_repo is not None

    @pytest.mark.asyncio
    async def test_clear_repository_multiple_repos(self, stores):
        """Test that clearing one repository doesn't affect others."""
        metadata_store, vector_store = stores
        repo_manager = RepositoryManager(metadata_store, vector_store)

        # Create two repositories
        repo1 = await repo_manager.create_repository(
            name="repo-1",
            description="Repository 1",
        )
        repo2 = await repo_manager.create_repository(
            name="repo-2",
            description="Repository 2",
        )

        # Add document to repo1
        from memory.core.models import Chunk, Embedding

        doc1 = Document(
            repository_id=repo1.id,
            source_path="/path/to/doc1.txt",
            doc_type=DocumentType.TEXT,
            title="Document 1",
            content="Content of document 1",
        )
        await metadata_store.add_document(doc1)

        chunk1 = Chunk(
            repository_id=repo1.id,
            document_id=doc1.id,
            content="Chunk 1 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )
        await metadata_store.add_chunk(chunk1)

        embedding1 = Embedding(
            chunk_id=chunk1.id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )
        await vector_store.add_embedding(embedding1, chunk1)

        # Add document to repo2
        doc2 = Document(
            repository_id=repo2.id,
            source_path="/path/to/doc2.txt",
            doc_type=DocumentType.TEXT,
            title="Document 2",
            content="Content of document 2",
        )
        await metadata_store.add_document(doc2)

        chunk2 = Chunk(
            repository_id=repo2.id,
            document_id=doc2.id,
            content="Chunk 2 content",
            chunk_index=0,
            start_char=0,
            end_char=15,
        )
        await metadata_store.add_chunk(chunk2)

        embedding2 = Embedding(
            chunk_id=chunk2.id,
            vector=[0.4, 0.5, 0.6],
            model="test-model",
            dimension=3,
        )
        await vector_store.add_embedding(embedding2, chunk2)

        # Clear repo1
        deleted_count = await repo_manager.clear_repository(repo1.id)
        assert deleted_count == 1

        # Verify repo1 is empty
        docs1 = await metadata_store.list_documents(repository_id=repo1.id)
        assert len(docs1) == 0

        # Verify repo2 still has documents
        docs2 = await metadata_store.list_documents(repository_id=repo2.id)
        assert len(docs2) == 1

        # Verify repo2 still has embeddings
        count = await vector_store.count()
        assert count == 1

        # Verify both repositories still exist
        retrieved_repo1 = await repo_manager.get_repository(repo1.id)
        retrieved_repo2 = await repo_manager.get_repository(repo2.id)
        assert retrieved_repo1 is not None
        assert retrieved_repo2 is not None
