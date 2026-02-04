"""End-to-end tests for complete import and search workflow."""

import pytest
import tempfile
import shutil
from pathlib import Path
from memory.config.loader import load_config
from memory.config.schema import AppConfig, EmbeddingConfig, VectorStoreConfig, MetadataStoreConfig, ChunkingConfig
from memory.core.models import Document, DocumentType, Repository
from memory.core.repository import RepositoryManager
from memory.core.chunking import create_chunks
from memory.pipelines.ingestion import IngestionPipeline
from memory.pipelines.query import QueryPipeline
from memory.providers.local import LocalEmbeddingProvider
from memory.providers.base import ProviderConfig
from memory.storage.chroma import ChromaVectorStore
from memory.storage.sqlite import SQLiteMetadataStore
from memory.storage.base import StorageConfig


@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    async def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    async def config(self, temp_dir):
        """Create a test configuration."""
        return AppConfig(
            app_name="memory-test",
            log_level="INFO",
            data_dir=str(temp_dir),
            default_repository="default",
            embedding=EmbeddingConfig(
                provider="local",
                model_name="all-MiniLM-L6-v2",
                batch_size=32,
            ),
            vector_store=VectorStoreConfig(
                store_type="chroma",
                collection_name="memory_test",
                extra_params={"persist_directory": str(temp_dir / "chroma")},
            ),
            metadata_store=MetadataStoreConfig(
                store_type="sqlite",
                extra_params={"connection_string": f"sqlite:///{temp_dir}/memory.db"},
            ),
            chunking=ChunkingConfig(
                chunk_size=256,
                chunk_overlap=50,
                min_chunk_size=50,
            ),
        )

    @pytest.fixture
    async def setup_stores(self, config):
        """Setup vector and metadata stores."""
        vector_store = ChromaVectorStore(
            collection_name=config.vector_store.collection_name,
            persist_directory=config.vector_store.extra_params["persist_directory"],
        )
        await vector_store.initialize()

        metadata_store = SQLiteMetadataStore(
            connection_string=config.metadata_store.extra_params["connection_string"],
        )
        await metadata_store.initialize()

        yield vector_store, metadata_store

        await vector_store.close()
        await metadata_store.close()

    @pytest.fixture
    async def embedding_provider(self):
        """Create an embedding provider."""
        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
        yield provider
        await provider.close()

    async def test_complete_import_and_search_workflow(
        self, config, setup_stores, embedding_provider
    ):
        """Test complete workflow: import documents and search."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("test-repo")

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Create test documents
        documents = [
            Document(
                content="Python is a high-level programming language known for its simplicity and readability.",
                source_path="python.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
            Document(
                content="Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                source_path="ml.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
            Document(
                content="Deep learning uses neural networks with multiple layers to process complex patterns.",
                source_path="dl.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
        ]

        # Ingest documents
        total_chunks = 0
        for doc in documents:
            num_chunks = await pipeline.ingest_document(doc)
            total_chunks += num_chunks
            assert num_chunks > 0

        assert total_chunks > 0

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search for Python-related content
        results = await query_pipeline.search("Python programming", top_k=5)

        assert len(results) > 0
        assert results[0].score > 0  # Should have similarity score

    async def test_multi_document_import_and_search(
        self, config, setup_stores, embedding_provider
    ):
        """Test importing multiple documents and searching across them."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("multi-doc-repo")

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Create multiple documents
        documents = [
            Document(
                content="The cat sat on the mat. The cat was very comfortable.",
                source_path="cat.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
            Document(
                content="Dogs are loyal pets. They love to play and run.",
                source_path="dog.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
            Document(
                content="Birds can fly high in the sky. They sing beautiful songs.",
                source_path="bird.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            ),
        ]

        # Ingest all documents
        for doc in documents:
            await pipeline.ingest_document(doc)

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search for cat-related content
        results = await query_pipeline.search("cat on mat", top_k=3)

        assert len(results) > 0
        # First result should be from cat document
        assert "cat" in results[0].chunk.content.lower()

    async def test_repository_isolation_workflow(
        self, config, setup_stores, embedding_provider
    ):
        """Test that different repositories are properly isolated."""
        vector_store, metadata_store = setup_stores

        # Create two repositories
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repo_a = await repo_manager.create_repository("repo-a", "Repository A")
        repo_b = await repo_manager.create_repository("repo-b", "Repository B")

        # Create pipelines for each repository
        pipeline_a = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repo_a.id,
        )

        pipeline_b = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repo_b.id,
        )

        # Ingest different documents to each repository
        doc_a = Document(
            content="Python is a programming language.",
            source_path="python.md",
            document_type=DocumentType.TEXT,
            repository_id=repo_a.id,
        )

        doc_b = Document(
            content="JavaScript is a web programming language.",
            source_path="javascript.md",
            document_type=DocumentType.TEXT,
            repository_id=repo_b.id,
        )

        await pipeline_a.ingest_document(doc_a)
        await pipeline_b.ingest_document(doc_b)

        # Create query pipelines for each repository
        query_a = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repo_a.id,
        )

        query_b = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repo_b.id,
        )

        # Search in repo-a for Python
        results_a = await query_a.search("Python", top_k=5)
        assert len(results_a) > 0
        assert "python" in results_a[0].chunk.content.lower()

        # Search in repo-b for JavaScript
        results_b = await query_b.search("JavaScript", top_k=5)
        assert len(results_b) > 0
        assert "javascript" in results_b[0].chunk.content.lower()

    async def test_chunking_and_search_accuracy(
        self, config, setup_stores, embedding_provider
    ):
        """Test that chunking works correctly and search is accurate."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("chunk-test-repo")

        # Create a long document that will be chunked
        long_content = """
        Chapter 1: Introduction to Machine Learning
        Machine learning is a subset of artificial intelligence that focuses on enabling
        computers to learn from data without being explicitly programmed. It has become
        increasingly important in modern applications.

        Chapter 2: Types of Machine Learning
        There are three main types of machine learning: supervised learning, unsupervised
        learning, and reinforcement learning. Each type has its own applications and
        challenges.

        Chapter 3: Deep Learning
        Deep learning is a specialized branch of machine learning that uses neural networks
        with multiple layers. It has achieved remarkable success in image recognition,
        natural language processing, and other domains.
        """

        document = Document(
            content=long_content,
            source_path="ml_guide.md",
            document_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Ingest document
        num_chunks = await pipeline.ingest_document(document)

        # Should have multiple chunks
        assert num_chunks > 1

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search for specific topics
        results_ml = await query_pipeline.search("machine learning types", top_k=3)
        assert len(results_ml) > 0

        results_dl = await query_pipeline.search("deep learning neural networks", top_k=3)
        assert len(results_dl) > 0

    async def test_large_scale_import_and_search(
        self, config, setup_stores, embedding_provider
    ):
        """Test importing and searching a large number of documents."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("large-scale-repo")

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Create and ingest many documents
        num_docs = 20
        for i in range(num_docs):
            doc = Document(
                content=f"Document {i}: This is a test document about topic {i % 5}. "
                f"It contains information relevant to category {i % 3}.",
                source_path=f"doc_{i}.md",
                document_type=DocumentType.TEXT,
                repository_id=repository.id,
            )
            await pipeline.ingest_document(doc)

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search
        results = await query_pipeline.search("topic 2", top_k=10)

        assert len(results) > 0
        assert len(results) <= 10

    async def test_delete_and_reindex_workflow(
        self, config, setup_stores, embedding_provider
    ):
        """Test deleting documents and verifying search results update."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("delete-test-repo")

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Ingest documents
        doc1 = Document(
            content="Document about cats and their behavior.",
            source_path="cats.md",
            document_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        doc2 = Document(
            content="Document about dogs and their training.",
            source_path="dogs.md",
            document_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        await pipeline.ingest_document(doc1)
        await pipeline.ingest_document(doc2)

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search before deletion
        results_before = await query_pipeline.search("animals", top_k=10)
        count_before = len(results_before)

        # Delete one document
        await metadata_store.delete_document(doc1.id)
        await vector_store.delete_by_document_id(
            doc1.id, repository_name="delete-test-repo"
        )

        # Search after deletion
        results_after = await query_pipeline.search("animals", top_k=10)
        count_after = len(results_after)

        # Should have fewer results
        assert count_after < count_before

    async def test_search_with_no_results(
        self, config, setup_stores, embedding_provider
    ):
        """Test searching for content that doesn't exist."""
        vector_store, metadata_store = setup_stores

        # Create repository
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("empty-search-repo")

        # Create query pipeline without ingesting any documents
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        # Search should return empty results
        results = await query_pipeline.search("nonexistent content", top_k=5)

        assert results == []

    async def test_persistence_across_sessions(
        self, config, setup_stores, embedding_provider, temp_dir
    ):
        """Test that data persists across different sessions."""
        vector_store, metadata_store = setup_stores

        # First session: ingest documents
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repository = await repo_manager.ensure_default_repository("persist-repo")

        pipeline = IngestionPipeline(
            config=config,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        doc = Document(
            content="Persistent document content for testing.",
            source_path="persistent.md",
            document_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        await pipeline.ingest_document(doc)

        # Close stores
        await vector_store.close()
        await metadata_store.close()

        # Second session: reopen stores and search
        vector_store2 = ChromaVectorStore(
            collection_name=config.vector_store.collection_name,
            persist_directory=config.vector_store.extra_params["persist_directory"],
        )
        await vector_store2.initialize()

        metadata_store2 = SQLiteMetadataStore(
            connection_string=config.metadata_store.extra_params["connection_string"],
        )
        await metadata_store2.initialize()

        # Get repository again
        repo_manager2 = RepositoryManager(metadata_store2, vector_store2)
        repository2 = await repo_manager2.get_repository_by_name("persist-repo")

        # Create query pipeline
        query_pipeline = QueryPipeline(
            embedding_provider=embedding_provider,
            vector_store=vector_store2,
            metadata_store=metadata_store2,
            repository_id=repository2.id,
        )

        # Search should find the document
        results = await query_pipeline.search("persistent document", top_k=5)

        assert len(results) > 0

        # Cleanup
        await vector_store2.close()
        await metadata_store2.close()
