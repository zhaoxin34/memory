"""Unit tests for ChromaVectorStore."""

import pytest
import tempfile
import shutil
from pathlib import Path
from memory.storage.chroma import ChromaVectorStore
from memory.storage.base import StorageConfig
from memory.core.models import Embedding


@pytest.mark.asyncio
class TestChromaVectorStore:
    """Test ChromaVectorStore functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    async def store(self, temp_dir):
        """Create a ChromaVectorStore instance for testing."""
        store = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store.initialize()
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test store initialization."""
        store = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store.initialize()

        assert store.base_collection_name == "test"
        assert store.persist_directory == str(temp_dir)
        assert store._client is not None

        await store.close()

    @pytest.mark.asyncio
    async def test_add_embedding(self, store):
        """Test adding a single embedding."""
        from memory.core.models import Chunk
        from uuid import UUID

        chunk = Chunk(
            repository_id=UUID("12345678-1234-5678-1234-567812345678"),
            document_id=UUID("12345678-1234-5678-1234-567812345678"),
            content="Test content",
            chunk_index=0,
            start_char=0,
            end_char=11,
        )
        embedding = Embedding(
            chunk_id=chunk.id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )

        await store.add_embedding(embedding, chunk)

        # Verify it was added
        count = await store.count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_embeddings_batch(self, store):
        """Test adding multiple embeddings."""
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                document_id=f"doc-{i}",
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                dimension=3,
            )
            for i in range(1, 6)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Verify they were added
        count = await store.count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_search(self, store):
        """Test similarity search."""
        # Add some embeddings
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                document_id=f"doc-{i}",
                vector=[float(i), float(i * 2), float(i * 3)],
                dimension=3,
            )
            for i in range(1, 6)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Search for similar vectors
        query_vector = [1.0, 2.0, 3.0]  # Should be closest to chunk-1
        results = await store.search(
            query_vector=query_vector,
            top_k=3,
            repository_name="test-repo",
        )

        assert len(results) == 3
        assert results[0]["chunk_id"] == "chunk-1"  # Closest match
        assert all("score" in r for r in results)
        assert all("chunk_id" in r for r in results)

    @pytest.mark.asyncio
    async def test_search_with_repository_filter(self, store):
        """Test search with repository filtering."""
        # Add embeddings to different repositories
        for repo_name in ["repo-a", "repo-b"]:
            embeddings = [
                Embedding(
                    chunk_id="f""{repo_name}-chunk-{i}",
                    document_id=f"{repo_name}-doc-{i}",
                    vector=[float(i), float(i * 2), float(i * 3)],
                    dimension=3,
                )
                for i in range(1, 4)
            ]
            await store.add_embeddings_batch(embeddings, repository_name=repo_name)

        # Search in repo-a only
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_name="repo-a",
        )

        assert len(results) == 3
        assert all("repo-a" in r["chunk_id"] for r in results)

    @pytest.mark.asyncio
    async def test_delete_by_chunk_id(self, store):
        """Test deleting by chunk ID."""
        # Add embeddings
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i in range(1, 4)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Delete one chunk
        await store.delete_by_chunk_id("chunk-1", repository_name="test-repo")

        # Verify count
        count = await store.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_by_document_id(self, store):
        """Test deleting by document ID."""
        # Add embeddings from different documents
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                document_id=f"doc-{i % 2}",  # doc-0 and doc-1,
                vector=[float(i), float(i * 2), float(i * 3)],
                dimension=3,
            )
            for i in range(1, 6)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Delete all chunks from doc-0
        await store.delete_by_document_id("doc-0", repository_name="test-repo")

        # Verify count (should have 2 chunks from doc-1 remaining)
        count = await store.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_by_repository(self, store):
        """Test deleting all embeddings from a repository."""
        # Add embeddings to multiple repositories
        for repo_name in ["repo-a", "repo-b"]:
            embeddings = [
                Embedding(
                    chunk_id="f""{repo_name}-chunk-{i}",
                    document_id=f"{repo_name}-doc-{i}",
                    vector=[float(i), float(i * 2), float(i * 3)],
                    dimension=3,
                )
                for i in range(1, 4)
            ]
            await store.add_embeddings_batch(embeddings, repository_name=repo_name)

        # Delete repo-a
        await store.delete_by_repository(repository_name="repo-a")

        # Verify repo-a is empty
        count_a = await store.count()
        assert count_a == 0

        # Verify repo-b still has data
        count_b = await store.count()
        assert count_b == 3

    @pytest.mark.asyncio
    async def test_count(self, store):
        """Test counting embeddings."""
        # Initially empty
        count = await store.count()
        assert count == 0

        # Add some embeddings
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i in range(1, 11)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Verify count
        count = await store.count()
        assert count == 10

    @pytest.mark.asyncio
    async def test_repository_isolation(self, store):
        """Test that repositories are properly isolated."""
        # Add embeddings to different repositories
        for repo_name in ["repo-a", "repo-b", "repo-c"]:
            embeddings = [
                Embedding(
                    chunk_id="f""{repo_name}-chunk-{i}",
                    document_id=f"{repo_name}-doc-{i}",
                    vector=[float(i), float(i * 2), float(i * 3)],
                    dimension=3,
                )
                for i in range(1, 4)
            ]
            await store.add_embeddings_batch(embeddings, repository_name=repo_name)

        # Verify each repository has correct count
        for repo_name in ["repo-a", "repo-b", "repo-c"]:
            count = await store.count(repository_name=repo_name)
            assert count == 3

        # Search in each repository
        query_vector = [1.0, 2.0, 3.0]
        for repo_name in ["repo-a", "repo-b", "repo-c"]:
            results = await store.search(
                query_vector=query_vector,
                top_k=5,
                repository_name=repo_name,
            )
            assert len(results) == 3
            assert all(repo_name in r["chunk_id"] for r in results)

    @pytest.mark.asyncio
    async def test_collection_name_sanitization(self, temp_dir):
        """Test that collection names are properly sanitized."""
        # Test with invalid characters
        store = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test-collection",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store.initialize()

        # Should work with sanitized name
        embedding = Embedding(
            chunk_id="12345678-1234-5678-1234-567812345678",
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )

        await store.add_embedding(embedding, repository_name="my-repo")
        count = await store.count()
        assert count == 1

        await store.close()

    @pytest.mark.asyncio
    async def test_persistence(self, temp_dir):
        """Test that data persists across store instances."""
        # Create store and add data
        store1 = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store1.initialize()

        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i in range(1, 6)
        ]

        await store1.add_embeddings_batch(embeddings, repository_name="test-repo")
        await store1.close()

        # Create new store instance with same directory
        store2 = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store2.initialize()

        # Verify data persisted
        count = await store2.count()
        assert count == 5

        await store2.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_dir):
        """Test using store as context manager."""
        async with ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        ) as store:
            await store.initialize()

            embedding = Embedding(
                chunk_id="12345678-1234-5678-1234-567812345678",
                vector=[0.1, 0.2, 0.3],
                model="test-model",
                dimension=3,
            )

            await store.add_embedding(embedding, repository_name="test-repo")
            count = await store.count()
            assert count == 1

    @pytest.mark.asyncio
    async def test_empty_search(self, store):
        """Test search on empty collection."""
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_name="empty-repo",
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_large_batch(self, store):
        """Test adding a large batch of embeddings."""
        # Create a large batch
        embeddings = [
            Embedding(
                chunk_id="f""chunk-{i}",
                document_id=f"doc-{i // 10}",
                vector=[float(i % 10), float((i % 10) * 2), float((i % 10) * 3)],
                dimension=3,
            )
            for i in range(1000)
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Verify count
        count = await store.count()
        assert count == 1000

        # Verify search still works
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=10,
            repository_name="test-repo",
        )

        assert len(results) == 10
