"""Tests for recall/retrieval accuracy.

This module contains test cases to validate the semantic search
retrieval accuracy of the knowledge base system.
"""

import asyncio
from pathlib import Path

import pytest

from memory.config.loader import load_config
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store

# Test data directory
TEST_DOCS_DIR = Path(__file__).parent.parent / "test_docs"

# Repository name for testing
TEST_REPO_NAME = "test-recall"

# Test queries and expected relevant documents
# Each entry: (query, list of expected document name prefixes)
TEST_CASES = [
    # Python related
    (
        "如何用async await写异步代码",
        ["python-async"],
    ),
    (
        "Python类型注解怎么用 TypeVar Generic",
        ["python-type-hints"],
    ),
    # JavaScript related
    (
        "箭头函数的使用方法 const let",
        ["javascript-es6"],
    ),
    # Cooking related
    (
        "红烧肉怎么做才好吃",
        ["cooking-hongshaorou"],
    ),
    # Fitness related
    (
        "如何进行力量训练增肌 深蹲卧推",
        ["fitness-strength"],
    ),
    # Design patterns
    (
        "单例模式和工厂模式的区别 装饰器模式",
        ["reading-notes-design-patterns"],
    ),
    # Cross-topic (should not confuse)
    (
        "日本料理和红烧肉的做法",
        ["cooking-hongshaorou", "travel-japan"],  # May retrieve both
    ),
]


def load_test_config() -> None:
    """Load configuration for tests."""
    from pathlib import Path

    return load_config(config_path=Path("/Volumes/data/working/life/memory/config.toml"))


class TestRecallAccuracy:
    """Test suite for semantic search recall accuracy."""

    @pytest.fixture(scope="class")
    def config(self):
        """Load configuration."""
        return load_test_config()

    @pytest.fixture(scope="class")
    async def query_pipeline(self, config):
        """Set up query pipeline for testing."""
        # Get API key - use environment variable name from config or default
        api_key = config.embedding.api_key or "BAILIAN_API_KEY"

        provider_config = ProviderConfig(
            provider_type=config.embedding.provider,
            model_name=config.embedding.model_name,
            api_key=api_key,
            extra_params=config.embedding.extra_params,
        )
        embedding_provider = create_embedding_provider(provider_config)
        vector_store = create_vector_store(config.vector_store)
        metadata_store = create_metadata_store(config.metadata_store)

        # Initialize stores
        await vector_store.initialize()
        await metadata_store.initialize()

        # Get repository by name
        repository = await metadata_store.get_repository_by_name(TEST_REPO_NAME)
        if not repository:
            pytest.skip(f"Repository '{TEST_REPO_NAME}' not found. Please create it first.")

        # Create query pipeline
        pipeline = QueryPipeline(
            config=config,
            embedding_provider=embedding_provider,
            llm_provider=None,  # Not needed for search
            vector_store=vector_store,
            metadata_store=metadata_store,
            repository_id=repository.id,
        )

        yield pipeline

        # Cleanup
        await vector_store.close()
        await metadata_store.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_prefixes", TEST_CASES)
    async def test_recall_accuracy(self, query_pipeline, query, expected_prefixes):
        """Test that search retrieves relevant documents.

        Args:
            query_pipeline: Query pipeline fixture
            query: The search query
            expected_prefixes: List of document name prefixes that should be retrieved
        """
        # Perform semantic search
        results = await query_pipeline.search(query, top_k=3)

        # Extract document names from results
        retrieved_names = [
            Path(result.document.source_path).stem
            for result in results
        ]

        # Check if any expected document is in the top results
        matched = any(
            any(name.startswith(prefix) for prefix in expected_prefixes)
            for name in retrieved_names
        )

        # For debugging
        print(f"\nQuery: {query}")
        print(f"Expected prefixes: {expected_prefixes}")
        print(f"Retrieved: {retrieved_names}")

        assert matched, (
            f"Query '{query}' did not retrieve any expected document. "
            f"Expected prefixes: {expected_prefixes}, Got: {retrieved_names}"
        )

    @pytest.mark.asyncio
    async def test_topic_discrimination(self, query_pipeline):
        """Test that different topics are correctly discriminated."""
        # Query about Python
        python_results = await query_pipeline.search("Python异步编程", top_k=3)
        python_docs = [Path(r.document.source_path).stem for r in python_results]

        # Query about cooking
        cooking_results = await query_pipeline.search("红烧肉做法", top_k=3)
        cooking_docs = [Path(r.document.source_path).stem for r in cooking_results]

        print(f"\nPython query results: {python_docs}")
        print(f"Cooking query results: {cooking_docs}")

        # Python query should retrieve Python docs
        assert any("python" in doc for doc in python_docs), (
            f"Python query did not retrieve Python docs: {python_docs}"
        )

        # Cooking query should retrieve cooking docs
        assert any("cooking" in doc or "hongshaorou" in doc for doc in cooking_docs), (
            f"Cooking query did not retrieve cooking docs: {cooking_docs}"
        )


# Standalone test runner for manual execution
async def run_recall_tests():
    """Run recall tests and print results."""
    config = load_test_config()

    # Create providers and stores
    api_key = config.embedding.api_key or "BAILIAN_API_KEY"

    provider_config = ProviderConfig(
        provider_type=config.embedding.provider,
        model_name=config.embedding.model_name,
        api_key=api_key,
        extra_params=config.embedding.extra_params,
    )
    embedding_provider = create_embedding_provider(provider_config)
    vector_store = create_vector_store(config.vector_store)
    metadata_store = create_metadata_store(config.metadata_store)

    # Initialize stores
    await vector_store.initialize()
    await metadata_store.initialize()

    # Get repository by name
    repository = await metadata_store.get_repository_by_name(TEST_REPO_NAME)
    if not repository:
        print(f"Error: Repository '{TEST_REPO_NAME}' not found.")
        print("Please create it first with: memory repo create test-recall")
        return

    print(f"Using repository: {repository.name} (ID: {repository.id})")

    # Create query pipeline
    query_pipeline = QueryPipeline(
        config=config,
        embedding_provider=embedding_provider,
        llm_provider=None,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repository.id,
    )

    # Run tests
    print("\n" + "=" * 60)
    print("Running recall tests...")
    print("=" * 60)

    passed = 0
    failed = 0

    for query, expected_prefixes in TEST_CASES:
        results = await query_pipeline.search(query, top_k=3)
        retrieved_names = [
            Path(result.document.source_path).stem
            for result in results
        ]

        matched = any(
            any(name.startswith(prefix) for prefix in expected_prefixes)
            for name in retrieved_names
        )

        status = "✓ PASS" if matched else "✗ FAIL"
        print(f"\n{status}: {query}")
        print(f"  Expected: {expected_prefixes}")
        print(f"  Retrieved: {retrieved_names}")

        if matched:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    # Cleanup
    await vector_store.close()
    await metadata_store.close()


if __name__ == "__main__":
    asyncio.run(run_recall_tests())
