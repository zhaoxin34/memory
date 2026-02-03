"""Command-line interface for the memory knowledge base system.

Commands:
- ingest: Add documents to the knowledge base
- search: Perform semantic search
- ask: Ask questions with LLM-based answers
- info: Show system information
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from memory.config.loader import get_default_config_path, load_config
from memory.config.schema import AppConfig
from memory.observability.logging import configure_logging, get_logger

app = typer.Typer(
    name="memory",
    help="Personal knowledge base with semantic search and LLM-based QA",
    add_completion=False,
)

console = Console()
logger = get_logger(__name__)


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="File or directory to ingest"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursively ingest directory"),
):
    """Ingest documents into the knowledge base."""
    asyncio.run(_ingest_async(path, config_file, recursive))


async def _ingest_async(path: Path, config_file: Optional[Path], recursive: bool):
    """Async implementation of ingest command."""
    # Load configuration
    config = _load_config(config_file)

    # Initialize components
    from memory.pipelines.ingestion import IngestionPipeline

    # TODO: Initialize providers and stores based on config
    # This requires implementing concrete provider and store classes

    console.print(f"[yellow]Ingestion not yet fully implemented[/yellow]")
    console.print(f"Would ingest: {path}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of results"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Perform semantic search."""
    asyncio.run(_search_async(query, top_k, config_file))


async def _search_async(query: str, top_k: int, config_file: Optional[Path]):
    """Async implementation of search command."""
    config = _load_config(config_file)

    console.print(f"[yellow]Search not yet fully implemented[/yellow]")
    console.print(f"Query: {query}")
    console.print(f"Top K: {top_k}")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to answer"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of chunks to retrieve"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Ask a question and get an LLM-generated answer."""
    asyncio.run(_ask_async(question, top_k, config_file))


async def _ask_async(question: str, top_k: int, config_file: Optional[Path]):
    """Async implementation of ask command."""
    config = _load_config(config_file)

    console.print(f"[yellow]Ask not yet fully implemented[/yellow]")
    console.print(f"Question: {question}")


@app.command()
def info(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Show system information and configuration."""
    config = _load_config(config_file)

    table = Table(title="Memory System Information")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Data Directory", str(config.data_dir))
    table.add_row("Log Level", config.log_level)
    table.add_row("Embedding Provider", config.embedding.provider)
    table.add_row("Embedding Model", config.embedding.model_name)
    table.add_row("LLM Provider", config.llm.provider)
    table.add_row("LLM Model", config.llm.model_name)
    table.add_row("Vector Store", config.vector_store.store_type)
    table.add_row("Metadata Store", config.metadata_store.store_type)

    console.print(table)


def _load_config(config_file: Optional[Path]) -> AppConfig:
    """Load configuration and setup logging."""
    if config_file is None:
        config_file = get_default_config_path()

    config = load_config(config_file)
    configure_logging(level=config.log_level, json_logs=config.json_logs)

    return config


if __name__ == "__main__":
    app()
