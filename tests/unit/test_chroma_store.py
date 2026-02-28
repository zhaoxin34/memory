"""Unit tests for ChromaVectorStore."""

import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from memory.core.models import Embedding
from memory.storage.base import StorageConfig
from memory.storage.chroma import ChromaVectorStore


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
        from uuid import UUID

        from memory.core.models import Chunk

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
        from memory.core.models import Chunk

        # Create chunks for the embeddings
        chunks = [
            Chunk(
                repository_id=uuid4(),
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=0,
                start_char=0,
                end_char=15,
            )
            for i in range(1, 6)
        ]

        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks, start=1)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Verify they were added
        count = await store.count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_search(self, store):
        """Test similarity search."""
        from memory.core.models import Chunk

        # Use same repository_id for all chunks to store them in the same collection
        repository_id = uuid4()

        # Create chunks for the embeddings
        chunks = [
            Chunk(
                repository_id=repository_id,
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(5)
        ]

        # Add some embeddings
        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Search for similar vectors
        query_vector = [1.0, 2.0, 3.0]  # Should be closest to chunk with index 0
        results = await store.search(
            query_vector=query_vector,
            top_k=3,
            repository_id=repository_id,
        )

        assert len(results) == 3
        assert all(hasattr(r, 'score') for r in results)
        assert all(hasattr(r, 'chunk') for r in results)

    @pytest.mark.asyncio
    async def test_search_with_repository_filter(self, store):
        """Test search with repository filtering."""
        from memory.core.models import Chunk

        # Add embeddings to different repositories
        repo_a_id = uuid4()
        repo_b_id = uuid4()

        for repo_id in [repo_a_id, repo_b_id]:
            chunks = [
                Chunk(
                    repository_id=repo_id,
                    document_id=uuid4(),
                    content=f"Chunk {i} content",
                    chunk_index=i,
                    start_char=0,
                    end_char=15,
                )
                for i in range(1, 4)
            ]

            embeddings = [
                Embedding(
                    chunk_id=chunk.id,
                    vector=[float(i), float(i * 2), float(i * 3)],
                    model="test-model",
                    dimension=3,
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            await store.add_embeddings_batch(embeddings, chunks)

        # Search in repo-a only
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_id=repo_a_id,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete_by_chunk_id(self, store):
        """Test deleting by chunk ID."""
        from memory.core.models import Chunk

        # Use same repository_id for all chunks to store them in the same collection
        repository_id = uuid4()

        # Create chunks for the embeddings
        chunks = [
            Chunk(
                repository_id=repository_id,
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(3)
        ]

        # Add embeddings
        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Delete one chunk
        await store.delete_by_chunk_id(chunks[1].id)

        # Verify count
        count = await store.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_by_document_id(self, store):
        """Test deleting by document ID."""
        from memory.core.models import Chunk

        # Create document IDs
        doc_ids = [uuid4(), uuid4()]

        # Create chunks from different documents
        chunks = [
            Chunk(
                repository_id=uuid4(),
                document_id=doc_ids[i % 2],  # Alternate between the two documents
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(5)
        ]

        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Delete all chunks from doc_ids[0]
        await store.delete_by_document_id(doc_ids[0])

        # Verify count (should have chunks from doc_ids[1] remaining)
        count = await store.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_by_repository(self, store):
        """Test deleting all embeddings from a repository."""
        from memory.core.models import Chunk

        # Add embeddings to multiple repositories
        repo_a_id = uuid4()
        repo_b_id = uuid4()

        for repo_id in [repo_a_id, repo_b_id]:
            chunks = [
                Chunk(
                    repository_id=repo_id,
                    document_id=uuid4(),
                    content=f"Chunk {i} content",
                    chunk_index=i,
                    start_char=0,
                    end_char=15,
                )
                for i in range(1, 4)
            ]

            embeddings = [
                Embedding(
                    chunk_id=chunk.id,
                    vector=[float(i), float(i * 2), float(i * 3)],
                    model="test-model",
                    dimension=3,
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            await store.add_embeddings_batch(embeddings, chunks)

        # Delete repo-a
        await store.delete_by_repository(repository_id=repo_a_id)

        # Verify repo-a is empty
        count = await store.count()
        assert count == 3  # repo-b has 3

    @pytest.mark.asyncio
    async def test_count(self, store):
        """Test counting embeddings."""
        from memory.core.models import Chunk

        # Initially empty
        count = await store.count()
        assert count == 0

        # Create chunks
        chunks = [
            Chunk(
                repository_id=uuid4(),
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(10)
        ]

        # Add some embeddings
        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Verify count
        count = await store.count()
        assert count == 10

    @pytest.mark.asyncio
    async def test_repository_isolation(self, store):
        """Test that repositories are properly isolated."""
        from memory.core.models import Chunk

        # Add embeddings to different repositories
        repo_ids = [uuid4(), uuid4(), uuid4()]

        for repo_id in repo_ids:
            chunks = [
                Chunk(
                    repository_id=repo_id,
                    document_id=uuid4(),
                    content=f"Chunk {i} content",
                    chunk_index=i,
                    start_char=0,
                    end_char=15,
                )
                for i in range(1, 4)
            ]

            embeddings = [
                Embedding(
                    chunk_id=chunk.id,
                    vector=[float(i), float(i * 2), float(i * 3)],
                    model="test-model",
                    dimension=3,
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            await store.add_embeddings_batch(embeddings, chunks)

        # Verify total count across all repositories
        total_count = await store.count()
        assert total_count == 9  # 3 repos * 3 chunks each

        # Search in each repository
        query_vector = [1.0, 2.0, 3.0]
        for repo_id in repo_ids:
            results = await store.search(
                query_vector=query_vector,
                top_k=5,
                repository_id=repo_id,
            )
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_collection_name_sanitization(self, temp_dir):
        """Test that collection names are properly sanitized."""
        from memory.core.models import Chunk

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
        chunk_id = uuid4()
        chunk = Chunk(
            repository_id=uuid4(),
            document_id=uuid4(),
            content="Test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
        )
        embedding = Embedding(
            chunk_id=chunk_id,
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimension=3,
        )

        await store.add_embedding(embedding, chunk)
        count = await store.count()
        assert count == 1

        await store.close()

    @pytest.mark.asyncio
    async def test_persistence(self, temp_dir):
        """Test that data persists across store instances."""
        from memory.core.models import Chunk

        # Create store and add data
        store1 = ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        )
        await store1.initialize()

        chunks = [
            Chunk(
                repository_id=uuid4(),
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(5)
        ]

        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i), float(i * 2), float(i * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store1.add_embeddings_batch(embeddings, chunks)
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
        from memory.core.models import Chunk

        async with ChromaVectorStore(
            StorageConfig(
                storage_type="chroma",
                collection_name="test",
                extra_params={"persist_directory": str(temp_dir)}
            )
        ) as store:
            await store.initialize()

            chunk = Chunk(
                repository_id=uuid4(),
                document_id=uuid4(),
                content="Test content",
                chunk_index=0,
                start_char=0,
                end_char=12,
            )
            embedding = Embedding(
                chunk_id=chunk.id,
                vector=[0.1, 0.2, 0.3],
                model="test-model",
                dimension=3,
            )

            await store.add_embedding(embedding, chunk)
            count = await store.count()
            assert count == 1

    @pytest.mark.asyncio
    async def test_empty_search(self, store):
        """Test search on empty collection."""
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_id=uuid4(),
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_large_batch(self, store):
        """Test adding a large batch of embeddings."""
        from memory.core.models import Chunk

        # Use same repository_id for all chunks to store them in the same collection
        repository_id = uuid4()

        # Create a large batch
        chunks = [
            Chunk(
                repository_id=repository_id,
                document_id=uuid4(),
                content=f"Chunk {i} content",
                chunk_index=i,
                start_char=0,
                end_char=15,
            )
            for i in range(1000)
        ]

        embeddings = [
            Embedding(
                chunk_id=chunk.id,
                vector=[float(i % 10), float((i % 10) * 2), float((i % 10) * 3)],
                model="test-model",
                dimension=3,
            )
            for i, chunk in enumerate(chunks)
        ]

        await store.add_embeddings_batch(embeddings, chunks)

        # Verify count
        count = await store.count()
        assert count == 1000

        # Verify search still works
        query_vector = [1.0, 2.0, 3.0]
        results = await store.search(
            query_vector=query_vector,
            top_k=10,
            repository_id=repository_id,
        )

        assert len(results) == 10
