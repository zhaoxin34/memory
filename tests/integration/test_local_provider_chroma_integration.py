"""Integration tests for LocalEmbeddingProvider + ChromaVectorStore."""

import pytest
import tempfile
import shutil
from pathlib import Path
from memory.providers.local import LocalEmbeddingProvider
from memory.storage.chroma import ChromaVectorStore
from memory.core.models import Embedding


@pytest.mark.asyncio
class TestLocalProviderChromaIntegration:
    """Test integration of LocalEmbeddingProvider with ChromaVectorStore."""

    @pytest.fixture
    async def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    async def provider(self):
        """Create a LocalEmbeddingProvider instance."""
        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
        yield provider
        await provider.close()

    @pytest.fixture
    async def store(self, temp_dir):
        """Create a ChromaVectorStore instance."""
        store = ChromaVectorStore(
            collection_name="test",
            persist_directory=str(temp_dir),
        )
        await store.initialize()
        yield store
        await store.close()

    async def test_embed_and_store(self, provider, store):
        """Test embedding text and storing in vector store."""
        text = "This is a test document about machine learning."

        # Embed the text
        vector = await provider.embed_text(text)

        # Create embedding object
        embedding = Embedding(
            chunk_id="chunk-1",
            document_id="doc-1",
            repository_id="repo-1",
            vector=vector,
            model_name=provider.model_name,
            dimension=provider.get_dimension(),
        )

        # Store the embedding
        await store.add_embedding(embedding, repository_name="test-repo")

        # Verify it was stored
        count = await store.count(repository_name="test-repo")
        assert count == 1

    async def test_batch_embed_and_store(self, provider, store):
        """Test batch embedding and storing."""
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing helps computers understand text.",
        ]

        # Batch embed
        vectors = await provider.embed_batch(texts)

        # Create embedding objects
        embeddings = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-1",
                vector=vectors[i],
                model_name=provider.model_name,
                dimension=provider.get_dimension(),
            )
            for i in range(len(texts))
        ]

        # Store all embeddings
        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Verify
        count = await store.count(repository_name="test-repo")
        assert count == 3

    async def test_search_similar_documents(self, provider, store):
        """Test searching for similar documents."""
        documents = [
            "The cat sat on the mat.",
            "A cat is sitting on a mat.",
            "Dogs are loyal pets.",
            "Python is a programming language.",
            "Java is also a programming language.",
        ]

        # Embed and store all documents
        vectors = await provider.embed_batch(documents)
        embeddings = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-1",
                vector=vectors[i],
                model_name=provider.model_name,
                dimension=provider.get_dimension(),
            )
            for i in range(len(documents))
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Search for similar to "cat on mat"
        query = "The cat is on the mat"
        query_vector = await provider.embed_text(query)

        results = await store.search(
            query_vector=query_vector,
            top_k=3,
            repository_name="test-repo",
        )

        # Should find cat-related documents first
        assert len(results) == 3
        assert results[0]["chunk_id"] in ["chunk-0", "chunk-1"]  # Cat documents
        assert results[1]["chunk_id"] in ["chunk-0", "chunk-1"]

    async def test_multi_repository_search(self, provider, store):
        """Test searching within specific repositories."""
        # Create documents for different repositories
        repo_a_docs = [
            "Python tutorial for beginners",
            "Advanced Python concepts",
        ]

        repo_b_docs = [
            "JavaScript basics",
            "Advanced JavaScript patterns",
        ]

        # Embed and store for repo-a
        vectors_a = await provider.embed_batch(repo_a_docs)
        embeddings_a = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-a",
                vector=vectors_a[i],
                model_name=provider.model_name,
                dimension=provider.get_dimension(),
            )
            for i in range(len(repo_a_docs))
        ]

        await store.add_embeddings_batch(embeddings_a, repository_name="repo-a")

        # Embed and store for repo-b
        vectors_b = await provider.embed_batch(repo_b_docs)
        embeddings_b = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-b",
                vector=vectors_b[i],
                model_name=provider.model_name,
                dimension=provider.get_dimension(),
            )
            for i in range(len(repo_b_docs))
        ]

        await store.add_embeddings_batch(embeddings_b, repository_name="repo-b")

        # Search for "Python" in repo-a only
        query_vector = await provider.embed_text("Python programming")

        results_a = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_name="repo-a",
        )

        results_b = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_name="repo-b",
        )

        # repo-a should have Python documents
        assert len(results_a) == 2
        assert all("chunk" in r["chunk_id"] for r in results_a)

        # repo-b should have JavaScript documents
        assert len(results_b) == 2
        assert all("chunk" in r["chunk_id"] for r in results_b)

    async def test_delete_and_search(self, provider, store):
        """Test deleting embeddings and verifying search results."""
        documents = [
            "Document about cats",
            "Document about dogs",
            "Document about birds",
        ]

        # Embed and store
        vectors = await provider.embed_batch(documents)
        embeddings = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-1",
                vector=vectors[i],
                model_name=provider.model_name,
                dimension=provider.get_dimension(),
            )
            for i in range(len(documents))
        ]

        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        # Verify initial count
        count = await store.count(repository_name="test-repo")
        assert count == 3

        # Delete one document
        await store.delete_by_document_id("doc-0", repository_name="test-repo")

        # Verify count decreased
        count = await store.count(repository_name="test-repo")
        assert count == 2

        # Search should only return remaining documents
        query_vector = await provider.embed_text("animals")
        results = await store.search(
            query_vector=query_vector,
            top_k=5,
            repository_name="test-repo",
        )

        assert len(results) == 2
        assert all(r["chunk_id"] in ["chunk-1", "chunk-2"] for r in results)

    async def test_large_scale_search(self, provider, store):
        """Test searching with a large number of documents."""
        # Create many documents
        documents = [
            f"Document {i}: This is a test document about topic {i % 10}"
            for i in range(100)
        ]

        # Embed in batches
        batch_size = 32
        all_embeddings = []

        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch_docs = documents[batch_start:batch_end]

            vectors = await provider.embed_batch(batch_docs)

            for i, vector in enumerate(vectors):
                doc_idx = batch_start + i
                embedding = Embedding(
                    chunk_id=f"chunk-{doc_idx}",
                    document_id=f"doc-{doc_idx}",
                    repository_id="repo-1",
                    vector=vector,
                    model_name=provider.model_name,
                    dimension=provider.get_dimension(),
                )
                all_embeddings.append(embedding)

        # Store all embeddings
        await store.add_embeddings_batch(all_embeddings, repository_name="test-repo")

        # Verify count
        count = await store.count(repository_name="test-repo")
        assert count == 100

        # Search
        query_vector = await provider.embed_text("topic 5")
        results = await store.search(
            query_vector=query_vector,
            top_k=10,
            repository_name="test-repo",
        )

        assert len(results) == 10
        assert all("score" in r for r in results)

    async def test_dimension_consistency(self, provider, store):
        """Test that embedding dimensions are consistent."""
        texts = ["Text 1", "Text 2", "Text 3"]

        # Get dimension from provider
        provider_dim = provider.get_dimension()

        # Embed texts
        vectors = await provider.embed_batch(texts)

        # Verify all vectors have correct dimension
        assert all(len(v) == provider_dim for v in vectors)

        # Create embeddings with correct dimension
        embeddings = [
            Embedding(
                chunk_id=f"chunk-{i}",
                document_id=f"doc-{i}",
                repository_id="repo-1",
                vector=vectors[i],
                model_name=provider.model_name,
                dimension=provider_dim,
            )
            for i in range(len(texts))
        ]

        # Store should accept them
        await store.add_embeddings_batch(embeddings, repository_name="test-repo")

        count = await store.count(repository_name="test-repo")
        assert count == 3
