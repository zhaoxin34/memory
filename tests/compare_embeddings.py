"""Compare recall results between OpenAI and BGE models."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from memory.config.loader import load_config
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.service import RepositoryManager
from memory.storage import create_metadata_store, create_vector_store

# Use relative path to config
CONFIG_PATH = Path(__file__).parent.parent / "config.toml"

TEST_CASES = [
    ("如何用async await写异步代码", ["python-async"]),
    ("Python类型注解怎么用 TypeVar Generic", ["python-type-hints"]),
    ("箭头函数的使用方法 const let", ["javascript-es6"]),
    ("红烧肉怎么做才好吃", ["cooking-hongshaorou"]),
    ("如何进行力量训练增肌 深蹲卧推", ["fitness-strength"]),
    ("单例模式和工厂模式的区别 装饰器模式", ["reading-notes-design-patterns"]),
]


@dataclass
class TestResult:
    query: str
    matched: bool
    retrieved_names: list[str]
    scores: list[float]


async def setup_stores():
    """Initialize stores - directly use storage layer."""
    config = load_config(config_path=CONFIG_PATH)

    metadata_store = create_metadata_store(config.metadata_store)
    vector_store = create_vector_store(config.vector_store)

    await metadata_store.initialize()
    await vector_store.initialize()

    return metadata_store, vector_store


async def get_or_create_repo(metadata_store, vector_store, repo_name: str):
    """Get or create repository - directly use core layer."""
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repository = await repo_manager.get_repository_by_name(repo_name)
    if not repository:
        repository = await repo_manager.create_repository(repo_name)
    return repository


def create_provider(model_name: str, provider_type: str, api_key: str | None = None):
    """Create embedding provider - directly use providers layer."""
    config = load_config(config_path=CONFIG_PATH)
    provider_config = ProviderConfig(
        provider_type=provider_type,
        model_name=model_name,
        api_key=api_key,
        extra_params=config.embedding.extra_params,
    )
    return create_embedding_provider(provider_config)


async def run_recall_test(query_pipeline, test_cases: list[tuple[str, list[str]]] | None = None) -> list[TestResult]:
    """Run recall test and return results."""
    test_cases = test_cases or TEST_CASES
    results = []

    for query, expected_prefixes in test_cases:
        search_results = await query_pipeline.search(query, top_k=3)
        retrieved_names = [
            Path(result.document.source_path).stem
            for result in search_results
        ]
        scores = [result.score for result in search_results]

        matched = any(
            any(name.startswith(prefix) for prefix in expected_prefixes)
            for name in retrieved_names
        )

        results.append(TestResult(
            query=query,
            matched=matched,
            retrieved_names=retrieved_names,
            scores=scores,
        ))

    return results


def print_test_results(repo_name: str, model_name: str, dimension: int, results: list[TestResult]) -> tuple[int, int]:
    """Print test results and return pass/fail counts."""
    print(f"\n{'='*70}")
    print(f"Repository: {repo_name}")
    print(f"Model: {model_name} (dimension: {dimension})")
    print(f"{'='*70}")

    passed = failed = 0
    for result in results:
        status = "✓ PASS" if result.matched else "✗ FAIL"
        print(f"\n{status}: {result.query}")
        print(f"  Retrieved: {result.retrieved_names}")
        print(f"  Scores: {[f'{s:.4f}' for s in result.scores]}")

        if result.matched:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*70}")
    print(f"Results: {passed}/{len(results)} passed ({passed/len(results)*100:.1f}%)")
    print(f"{'='*70}")

    return passed, failed


async def test_repo(
    metadata_store,
    vector_store,
    repo_name: str,
    model_name: str,
    provider_type: str,
    api_key: str | None = None,
) -> tuple[int, int, list[TestResult]]:
    """Test a specific repository with specific model."""
    config = load_config(config_path=CONFIG_PATH)

    # Use core layer (RepositoryManager) and pipelines layer (QueryPipeline)
    embedding_provider = create_provider(model_name, provider_type, api_key)
    repository = await get_or_create_repo(metadata_store, vector_store, repo_name)

    query_pipeline = QueryPipeline(
        config=config,
        embedding_provider=embedding_provider,
        llm_provider=None,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repository.id,
    )

    results = await run_recall_test(query_pipeline)
    passed, failed = print_test_results(repo_name, model_name, embedding_provider.get_dimension(), results)

    return passed, failed, results


async def main() -> None:
    # Use storage layer directly (not interfaces layer)
    metadata_store, vector_store = await setup_stores()

    try:
        # Test 1: OpenAI model on test-recall
        print("\n" + "="*70)
        print("TEST 1: OpenAI model (text-embedding-v4)")
        print("="*70)
        openai_result = await test_repo(
            metadata_store=metadata_store,
            vector_store=vector_store,
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
            metadata_store=metadata_store,
            vector_store=vector_store,
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
    finally:
        await vector_store.close()
        await metadata_store.close()


if __name__ == "__main__":
    asyncio.run(main())
