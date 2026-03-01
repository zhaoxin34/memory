"""RAG 评估脚本 - 基础检索评估。

使用方法:
    uv run python -m eval.evaluate eval/test_data.json

评估指标:
    - 平均检索分数 (Average Similarity Score)
    - 召回率 (基于关键词匹配)
    - 检索结果质量分析
"""

import asyncio
import json
import statistics
from pathlib import Path
from typing import Any

import jieba
import typer
from rich.console import Console
from rich.table import Table

from memory.config.loader import load_config
from memory.config.schema import AppConfig
from memory.core.logging import configure_from_config, get_logger
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider, create_llm_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store

console = Console()
logger = get_logger(__name__)


async def initialize_pipeline(config: AppConfig, repository_name: str | None = None) -> tuple[QueryPipeline, str | None]:
    """初始化查询管道及其依赖。

    Args:
        config: 应用配置
        repository_name: 可选的 repository 名称，用于限制搜索范围

    Returns:
        (QueryPipeline, repository_id) 元组
    """
    # 初始化存储
    metadata_store = create_metadata_store(config.metadata_store)
    vector_store = create_vector_store(config.vector_store)

    # 调用 initialize 方法
    await metadata_store.initialize()
    await vector_store.initialize()

    # 获取 repository_id
    repository_id = None
    if repository_name:
        from memory.service import RepositoryManager
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repo = await repo_manager.get_repository_by_name(repository_name)
        if repo:
            repository_id = repo.id
            console.print(f"[green]使用 repository: {repository_name}[/green]")
        else:
            console.print(f"[yellow]repository '{repository_name}' 不存在，将搜索所有仓库[/yellow]")

    # 初始化 embedding provider
    embedding_provider_config = ProviderConfig(
        provider_type=config.embedding.provider,
        model_name=config.embedding.model_name,
        api_key=config.embedding.api_key,
        extra_params=config.embedding.extra_params,
    )
    embedding_provider = create_embedding_provider(embedding_provider_config)

    # 初始化 LLM provider
    llm_provider_config = ProviderConfig(
        provider_type=config.llm.provider,
        model_name=config.llm.model_name,
        api_key=config.llm.api_key,
        extra_params=config.llm.extra_params,
    )
    llm_provider = create_llm_provider(llm_provider_config)

    return (
        QueryPipeline(
            config=config,
            embedding_provider=embedding_provider,
            llm_provider=llm_provider,
            vector_store=vector_store,
            metadata_store=metadata_store,
        ),
        repository_id,
    )


def load_test_data(file_path: Path) -> list[dict[str, Any]]:
    """加载测试数据集。"""
    with open(file_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("测试数据必须是问答对列表")

    # 验证每条数据
    for i, item in enumerate(data):
        if "question" not in item:
            raise ValueError(f"第 {i+1} 条数据缺少 'question' 字段")
        if "ground_truth" not in item:
            raise ValueError(f"第 {i+1} 条数据缺少 'ground_truth' 字段")

    return data


def extract_chinese_keywords(text: str) -> set[str]:
    """提取中文关键词（使用 jieba 分词）。

    Args:
        text: 输入文本

    Returns:
        关键词集合
    """
    # 使用 jieba 分词
    words = jieba.lcut(text)
    # 过滤停用词、单字、数字
    keywords = {
        w for w in words
        if len(w) > 1 and not w.isdigit() and w.strip()
    }
    return keywords


def calculate_keyword_recall(ground_truth: str, contexts: list[str]) -> float:
    """基于关键词匹配计算召回率。

    Args:
        ground_truth: 标准答案
        contexts: 检索到的上下文列表

    Returns:
        召回率 (0-1)
    """
    # 使用 jieba 提取关键词
    keywords = extract_chinese_keywords(ground_truth)

    if not keywords:
        return 0.0

    # 合并所有上下文
    all_context = " ".join(contexts)
    context_keywords = extract_chinese_keywords(all_context)

    # 计算有多少关键词出现在上下文中（去重）
    matched_keywords = keywords & context_keywords

    # 召回率 = 匹配的关键词数 / 总关键词数
    recall = len(matched_keywords) / len(keywords)
    return recall


def calculate_context_relevance(question: str, contexts: list[str]) -> float:
    """基于关键词匹配计算上下文与问题的相关性。

    Args:
        question: 问题
        contexts: 检索到的上下文列表

    Returns:
        相关性分数 (0-1)
    """
    # 使用 jieba 提取问题关键词
    question_keywords = extract_chinese_keywords(question)

    if not question_keywords:
        return 0.0

    # 合并所有上下文
    all_context = " ".join(contexts)
    context_keywords = extract_chinese_keywords(all_context)

    # 计算有多少问题关键词出现在上下文中
    matched = len(question_keywords & context_keywords)

    # 相关性 = 匹配的关键词数 / 问题关键词数
    return matched / len(question_keywords)


async def run_evaluation(
    test_data: list[dict[str, Any]],
    pipeline: QueryPipeline,
    top_k: int = 5,
    repository_id: str | None = None,
) -> list[dict[str, Any]]:
    """对每个测试问题运行评估。"""
    results = []

    for i, item in enumerate(test_data):
        question = item["question"]
        console.print(f"[{i+1}/{len(test_data)}] 评估: {question[:50]}...")

        try:
            # 获取检索结果
            search_results = await pipeline.search(
                question,
                top_k=top_k,
                repository_id=repository_id,
            )

            # 提取上下文和分数
            contexts = [result.chunk.content for result in search_results]
            scores = [result.score for result in search_results]

            result_item = {
                "question": question,
                "contexts": contexts,
                "scores": scores,
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "has_results": len(contexts) > 0,
            }

            # 添加 ground_truth（如果存在）
            if "ground_truth" in item:
                result_item["ground_truth"] = item["ground_truth"]
                result_item["keyword_recall"] = calculate_keyword_recall(
                    item["ground_truth"], contexts
                )

            # 计算上下文相关性
            if contexts:
                result_item["context_relevance"] = calculate_context_relevance(
                    question, contexts
                )

            results.append(result_item)

        except Exception as e:
            logger.error("eval_error", question=question, error=str(e))
            results.append({
                "question": question,
                "contexts": [],
                "scores": [],
                "avg_score": 0.0,
                "has_results": False,
                "error": str(e),
            })

    return results


def print_results(results: list[dict[str, Any]]) -> None:
    """打印评估结果表格。"""
    # 计算总体指标
    total = len(results)
    has_results = sum(1 for r in results if r.get("has_results", False))

    # 收集所有分数
    all_scores = []
    avg_scores = []
    for r in results:
        if r.get("has_results", False):
            scores = r.get("scores", [])
            all_scores.extend(scores)
            avg_scores.append(r["avg_score"])

    overall_avg_score = statistics.mean(avg_scores) if avg_scores else 0.0
    max_score = max(all_scores) if all_scores else 0.0
    min_score = min(all_scores) if all_scores else 0.0
    stddev = statistics.stdev(avg_scores) if len(avg_scores) > 1 else 0.0

    # 关键词召回率（如果有 ground_truth）
    recalls = [r["keyword_recall"] for r in results if "keyword_recall" in r]
    avg_keyword_recall = statistics.mean(recalls) if recalls else None

    # 上下文相关性
    relevances = [r["context_relevance"] for r in results if "context_relevance" in r]
    avg_relevance = statistics.mean(relevances) if relevances else None

    # 打印总体指标
    table = Table(title="检索评估结果")
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green")

    table.add_row("测试用例数", str(total))
    table.add_row("有结果数", f"{has_results}/{total}")
    table.add_row("平均相似度分数", f"{overall_avg_score:.4f}")
    table.add_row("最高分", f"{max_score:.4f}")
    table.add_row("最低分", f"{min_score:.4f}")
    table.add_row("分数标准差", f"{stddev:.4f}")

    if avg_keyword_recall is not None:
        table.add_row("平均关键词召回率", f"{avg_keyword_recall:.4f}")

    if avg_relevance is not None:
        table.add_row("平均上下文相关性", f"{avg_relevance:.4f}")

    console.print(table)

    # 打印每条结果的详情
    detail_table = Table(title="详细结果")
    detail_table.add_column("#", style="dim")
    detail_table.add_column("问题", style="white")
    detail_table.add_column("结果数", style="yellow")
    detail_table.add_column("平均分", style="green")
    detail_table.add_column("最高分", style="green")
    detail_table.add_column("最低分", style="green")
    detail_table.add_column("标准差", style="green")

    if avg_keyword_recall is not None:
        detail_table.add_column("召回率", style="blue")

    for i, r in enumerate(results, 1):
        question_short = r["question"][:25] + "..." if len(r["question"]) > 25 else r["question"]
        scores = r.get("scores", [])
        result_count = len(scores)
        avg_score = r.get("avg_score", 0.0)
        max_s = max(scores) if scores else 0.0
        min_s = min(scores) if scores else 0.0
        std = statistics.stdev(scores) if len(scores) > 1 else 0.0

        row = [
            str(i),
            question_short,
            str(result_count),
            f"{avg_score:.3f}",
            f"{max_s:.3f}",
            f"{min_s:.3f}",
            f"{std:.3f}",
        ]

        if avg_keyword_recall is not None:
            recall = r.get("keyword_recall", 0.0)
            row.append(f"{recall:.2f}")

        detail_table.add_row(*row)

    console.print(detail_table)


async def evaluate_cmd(
    test_data: Path = typer.Argument(..., help="测试数据文件路径 (JSON)"),
    top_k: int = typer.Option(5, help="检索的上下文数量"),
    repository: str | None = typer.Option("test", help="要评估的 repository 名称"),
    output: Path | None = typer.Option(None, help="输出结果到 JSON 文件"),
) -> None:
    """运行 RAG 评估。"""
    # 加载配置
    config = load_config()
    configure_from_config(config.logging)

    console.print("[yellow]正在初始化管道...[/yellow]")
    pipeline, repository_id = await initialize_pipeline(config, repository)

    # 加载测试数据
    console.print(f"[yellow]加载测试数据: {test_data}[/yellow]")
    test_cases = load_test_data(test_data)
    console.print(f"[yellow]已加载 {len(test_cases)} 条测试用例[/yellow]")

    # 运行评估
    console.print("[yellow]运行评估...[/yellow]")
    results = await run_evaluation(test_cases, pipeline, top_k=top_k, repository_id=repository_id)

    # 打印结果
    print_results(results)

    # 保存结果
    if output:
        with open(output, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        console.print(f"[green]评估结果已保存到: {output}[/green]")


app = typer.Typer()


@app.command()
def main(
    test_data: Path = typer.Argument(..., help="测试数据文件路径 (JSON)"),
    top_k: int = typer.Option(5, help="检索的上下文数量"),
    repository: str | None = typer.Option("test", help="要评估的 repository 名称"),
    output: Path | None = typer.Option(None, help="输出结果到 JSON 文件"),
) -> None:
    """运行 RAG 评估。"""
    asyncio.run(evaluate_cmd(test_data, top_k, repository, output))


if __name__ == "__main__":
    app()
