"""Compare embedding models on recall accuracy."""

import asyncio
from pathlib import Path

from memory.config.loader import load_config
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store

# Test data directory
TEST_DOCS_DIR = Path(__file__).parent.parent / "test_docs"

# Repository to use
TEST_REPO_NAME = "test-recall"  # This has documents imported with openai

# Test queries
TEST_CASES = [
    ("如何用async await写异步代码", ["python-async"]),
    ("Python类型注解怎么用 TypeVar Generic", ["python-type-hints"]),
    ("箭头函数的使用方法 const let", ["javascript-es6"]),
    ("红烧肉怎么做才好吃", ["cooking-hongshaorou"]),
    ("如何进行力量训练增肌 深蹲卧推", ["fitness-strength"]),
    ("单例模式和工厂模式的区别 装饰器模式", ["reading-notes-design-patterns"]),
]


async def test_model(model_name: str, provider_type: str, api_key: str = None):
    """Test a specific embedding model."""
    config = load_config()

    # Create provider
    provider_config = ProviderConfig(
        provider_type=provider_type,
        model_name=model_name,
        api_key=api_key,
        extra_params=config.embedding.extra_params,
    )
    embedding_provider = create_embedding_provider(provider_config)

    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"Dimension: {embedding_provider.get_dimension()}")
    print(f"{'='*60}")

    # Create stores
    vector_store = create_vector_store(config.vector_store)
    metadata_store = create_metadata_store(config.metadata_store)

    await vector_store.initialize()
    await metadata_store.initialize()

    # Get repository
    repository = await metadata_store.get_repository_by_name(TEST_REPO_NAME)
    if not repository:
        print(f"Repository '{TEST_REPO_NAME}' not found")
        return

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
        print(f"{status}: {query}")
        print(f"  Expected: {expected_prefixes}")
        print(f"  Retrieved: {retrieved_names}")

        if matched:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    await vector_store.close()
    await metadata_store.close()


async def main():
    # Test 1: OpenAI API model (current)
    await test_model(
        model_name="text-embedding-v4",
        provider_type="openai",
        api_key="BAILIAN_API_KEY"
    )

    # Test 2: Local BGE model
    await test_model(
        model_name="BAAI/bge-small-zh-v1.5",
        provider_type="local",
    )


if __name__ == "__main__":
    asyncio.run(main())
