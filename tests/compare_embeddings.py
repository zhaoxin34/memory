"""Compare recall results between OpenAI and BGE models."""

import asyncio
from pathlib import Path

from memory.config.loader import load_config
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store

# Correct path to config
CONFIG_PATH = Path("/Volumes/data/working/life/memory/config.toml")

TEST_CASES = [
    ("如何用async await写异步代码", ["python-async"]),
    ("Python类型注解怎么用 TypeVar Generic", ["python-type-hints"]),
    ("箭头函数的使用方法 const let", ["javascript-es6"]),
    ("红烧肉怎么做才好吃", ["cooking-hongshaorou"]),
    ("如何进行力量训练增肌 深蹲卧推", ["fitness-strength"]),
    ("单例模式和工厂模式的区别 装饰器模式", ["reading-notes-design-patterns"]),
]


async def test_repo(
    repo_name: str,
    model_name: str,
    provider_type: str,
    api_key: str | None = None,
) -> tuple[int, int, list[tuple[str, bool, list[str], list[float]]]] | None:
    """Test a specific repository with specific model."""
    config = load_config(config_path=CONFIG_PATH)

    # Create provider
    provider_config = ProviderConfig(
        provider_type=provider_type,
        model_name=model_name,
        api_key=api_key,
        extra_params=config.embedding.extra_params,
    )
    embedding_provider = create_embedding_provider(provider_config)

    print(f"\n{'='*70}")
    print(f"Repository: {repo_name}")
    print(f"Model: {model_name} (dimension: {embedding_provider.get_dimension()})")
    print(f"{'='*70}")

    # Create stores
    vector_store = create_vector_store(config.vector_store)
    metadata_store = create_metadata_store(config.metadata_store)

    await vector_store.initialize()
    await metadata_store.initialize()

    # Get repository
    repository = await metadata_store.get_repository_by_name(repo_name)
    if not repository:
        print(f"Repository '{repo_name}' not found!")
        return None

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
    all_results = []

    for query, expected_prefixes in TEST_CASES:
        results = await query_pipeline.search(query, top_k=3)
        retrieved_names = [
            Path(result.document.source_path).stem
            for result in results
        ]
        scores = [result.score for result in results]

        matched = any(
            any(name.startswith(prefix) for prefix in expected_prefixes)
            for name in retrieved_names
        )

        status = "✓ PASS" if matched else "✗ FAIL"
        print(f"\n{status}: {query}")
        print(f"  Expected: {expected_prefixes}")
        print(f"  Retrieved: {retrieved_names}")
        print(f"  Scores: {[f'{s:.4f}' for s in scores]}")

        if matched:
            passed += 1
        else:
            failed += 1

        all_results.append((query, matched, retrieved_names, scores))

    print(f"\n{'='*70}")
    print(f"Results: {passed}/{len(TEST_CASES)} passed ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"{'='*70}")

    await vector_store.close()
    await metadata_store.close()

    return passed, failed, all_results


async def main() -> None:
    # Test 1: OpenAI model on test-recall
    print("\n" + "="*70)
    print("TEST 1: OpenAI model (text-embedding-v4)")
    print("="*70)
    openai_result = await test_repo(
        repo_name="test-recall",
        model_name="text-embedding-v4",
        provider_type="openai",
        api_key="BAILIAN_API_KEY"
    )

    # Test 2: BGE model on test-bge-small
    print("\n" + "="*70)
    print("TEST 2: BGE model (bge-small-zh-v1.5)")
    print("="*70)
    bge_result = await test_repo(
        repo_name="test-bge-small",
        model_name="BAAI/bge-small-zh-v1.5",
        provider_type="local",
    )

    # Summary
    if openai_result and bge_result:
        openai_passed, _, _ = openai_result
        bge_passed, _, _ = bge_result

        print("\n" + "="*70)
        print("SUMMARY COMPARISON")
        print("="*70)
        print(f"OpenAI (text-embedding-v4):    {openai_passed}/{len(TEST_CASES)} passed ({openai_passed/len(TEST_CASES)*100:.1f}%)")
        print(f"BGE (bge-small-zh-v1.5):      {bge_passed}/{len(TEST_CASES)} passed ({bge_passed/len(TEST_CASES)*100:.1f}%)")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
