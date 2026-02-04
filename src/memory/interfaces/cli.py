"""Command-line interface for the memory knowledge base system.

Commands:
- ingest: Add documents to the knowledge base
- search: Perform semantic search
- ask: Ask questions with LLM-based answers
- repo: Manage repositories
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


async def _ensure_default_repository(config: AppConfig):
    """Ensure default repository exists.

    This function initializes the metadata and vector stores,
    and ensures the default repository is created.

    Args:
        config: Application configuration

    Returns:
        Tuple of (metadata_store, vector_store, repository)
    """
    from memory.core.repository import RepositoryManager
    from memory.storage import create_metadata_store, create_vector_store
    from memory.storage.base import StorageConfig

    # Create storage configuration
    vector_storage_config = StorageConfig(
        storage_type=config.vector_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.vector_store.extra_params,
    )

    metadata_storage_config = StorageConfig(
        storage_type=config.metadata_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.metadata_store.extra_params,
    )

    # Create stores using factory functions
    try:
        metadata_store = create_metadata_store(metadata_storage_config)
        vector_store = create_vector_store(vector_storage_config)

        await metadata_store.initialize()
        await vector_store.initialize()

    except Exception as e:
        console.print(f"[red]Error initializing stores: {str(e)}[/red]")
        raise typer.Exit(1)

    # Ensure default repository exists
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repository = await repo_manager.ensure_default_repository(config.default_repository)

    logger.info("default_repository_ensured", repository_name=repository.name)

    return metadata_store, vector_store, repository


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="File or directory to ingest"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursively ingest directory"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name (defaults to config default_repository)"),
):
    """Ingest documents into the knowledge base."""
    asyncio.run(_ingest_async(path, config_file, recursive, repository))


async def _ingest_async(path: Path, config_file: Optional[Path], recursive: bool, repository: Optional[str]):
    """Async implementation of ingest command."""
    # Load configuration
    config = _load_config(config_file)

    # Ensure default repository exists
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Use provided repository or fall back to default
    repo_name = repository or config.default_repository

    # Get the repository object
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repo = await repo_manager.get_repository_by_name(repo_name)

    if not repo:
        console.print(f"[red]Repository '{repo_name}' not found[/red]")
        raise typer.Exit(1)

    # Create embedding provider
    try:
        from memory.providers import create_embedding_provider
        from memory.providers.base import ProviderConfig

        provider_config = ProviderConfig(
            provider_type=config.embedding.provider,
            model_name=config.embedding.model_name,
            api_key=config.embedding.api_key,
            extra_params=config.embedding.extra_params,
        )

        embedding_provider = create_embedding_provider(provider_config)

    except Exception as e:
        console.print(f"[red]Error creating embedding provider: {str(e)}[/red]")
        raise typer.Exit(1)

    # Initialize ingestion pipeline
    from memory.pipelines.ingestion import IngestionPipeline

    pipeline = IngestionPipeline(
        config=config,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repo.id,
    )

    # Collect files to ingest
    files_to_ingest = []

    if path.is_file():
        files_to_ingest.append(path)
    elif path.is_dir():
        if recursive:
            # Recursively find all files
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    files_to_ingest.append(file_path)
        else:
            # Only files in the directory
            for file_path in path.iterdir():
                if file_path.is_file():
                    files_to_ingest.append(file_path)
    else:
        console.print(f"[red]Path not found: {path}[/red]")
        raise typer.Exit(1)

    if not files_to_ingest:
        console.print(f"[yellow]No files found to ingest[/yellow]")
        return

    console.print(f"[cyan]Ingesting {len(files_to_ingest)} file(s) into repository '{repo_name}'...[/cyan]")

    # Ingest each file
    success_count = 0
    error_count = 0

    for file_path in files_to_ingest:
        try:
            console.print(f"  Processing: {file_path}")

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Create document object
            from memory.core.models import Document, DocumentType

            document = Document(
                content=content,
                source_path=str(file_path),
                document_type=DocumentType.TEXT,
                repository_id=repo.id,
            )

            # Ingest document
            num_chunks = await pipeline.ingest_document(document)

            console.print(f"  [green]✓[/green] Ingested: {file_path.name} ({num_chunks} chunks, ID: {document.id})")
            success_count += 1

        except UnicodeDecodeError:
            console.print(f"  [yellow]⚠[/yellow] Skipped (not a text file): {file_path.name}")
            error_count += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] Error: {file_path.name} - {str(e)}")
            error_count += 1
            logger.error("ingestion_error", file=str(file_path), error=str(e))

    # Summary
    console.print()
    console.print(f"[green]Successfully ingested: {success_count} file(s)[/green]")
    if error_count > 0:
        console.print(f"[yellow]Errors: {error_count} file(s)[/yellow]")

    # Cleanup
    await embedding_provider.close()
    await metadata_store.close()
    await vector_store.close()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of results"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name (defaults to config default_repository)"),
):
    """Perform semantic search."""
    asyncio.run(_search_async(query, top_k, config_file, repository))


async def _search_async(query: str, top_k: int, config_file: Optional[Path], repository: Optional[str]):
    """Async implementation of search command."""
    config = _load_config(config_file)

    # Ensure default repository exists
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Use provided repository or fall back to default
    repo_name = repository or config.default_repository

    # Get the repository object
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repo = await repo_manager.get_repository_by_name(repo_name)

    if not repo:
        console.print(f"[red]Repository '{repo_name}' not found[/red]")
        raise typer.Exit(1)

    # Create embedding provider
    try:
        from memory.providers import create_embedding_provider
        from memory.providers.base import ProviderConfig

        provider_config = ProviderConfig(
            provider_type=config.embedding.provider,
            model_name=config.embedding.model_name,
            api_key=config.embedding.api_key,
            extra_params=config.embedding.extra_params,
        )

        embedding_provider = create_embedding_provider(provider_config)

    except Exception as e:
        console.print(f"[red]Error creating embedding provider: {str(e)}[/red]")
        raise typer.Exit(1)

    # Initialize query pipeline
    from memory.pipelines.query import QueryPipeline

    pipeline = QueryPipeline(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
    )

    # Perform search
    try:
        console.print(f"[cyan]Searching in repository '{repo_name}'...[/cyan]")

        results = await pipeline.search(
            query=query,
            top_k=top_k,
            repository_id=repo.id,
        )

        if not results:
            console.print("[yellow]No results found[/yellow]")
        else:
            console.print(f"\n[green]Found {len(results)} result(s):[/green]\n")

            for i, result in enumerate(results, 1):
                console.print(f"[bold cyan]{i}. Score: {result.score:.4f}[/bold cyan]")
                console.print(f"   Document ID: {result.document_id}")
                console.print(f"   Chunk: {result.chunk.text[:200]}...")
                console.print()

    except Exception as e:
        console.print(f"[red]Search error: {str(e)}[/red]")
        logger.error("search_error", error=str(e))
        raise typer.Exit(1)

    # Cleanup
    await embedding_provider.close()
    await metadata_store.close()
    await vector_store.close()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to answer"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of chunks to retrieve"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name (defaults to config default_repository)"),
):
    """Ask a question and get an LLM-generated answer."""
    asyncio.run(_ask_async(question, top_k, config_file, repository))


async def _ask_async(question: str, top_k: int, config_file: Optional[Path], repository: Optional[str]):
    """Async implementation of ask command."""
    config = _load_config(config_file)

    # Ensure default repository exists
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Use provided repository or fall back to default
    repo_name = repository or config.default_repository

    # Get the repository object
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repo = await repo_manager.get_repository_by_name(repo_name)

    if not repo:
        console.print(f"[red]Repository '{repo_name}' not found[/red]")
        raise typer.Exit(1)

    # Create embedding provider
    try:
        from memory.providers import create_embedding_provider
        from memory.providers.base import ProviderConfig

        embedding_provider_config = ProviderConfig(
            provider_type=config.embedding.provider,
            model_name=config.embedding.model_name,
            api_key=config.embedding.api_key,
            extra_params=config.embedding.extra_params,
        )

        embedding_provider = create_embedding_provider(embedding_provider_config)

    except Exception as e:
        console.print(f"[red]Error creating embedding provider: {str(e)}[/red]")
        raise typer.Exit(1)

    # Note: LLM provider not yet implemented, so we'll just show retrieved chunks
    console.print(f"[yellow]Note: LLM provider not yet implemented. Showing retrieved chunks only.[/yellow]\n")

    # Initialize query pipeline
    from memory.pipelines.query import QueryPipeline

    pipeline = QueryPipeline(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
        llm_provider=None,  # LLM not yet implemented
    )

    # Retrieve relevant chunks
    try:
        console.print(f"[cyan]Retrieving relevant information from repository '{repo_name}'...[/cyan]")

        results = await pipeline.search(
            query=question,
            top_k=top_k,
            repository_id=repo.id,
        )

        if not results:
            console.print("[yellow]No relevant information found[/yellow]")
        else:
            console.print(f"\n[green]Found {len(results)} relevant chunk(s):[/green]\n")

            for i, result in enumerate(results, 1):
                console.print(f"[bold cyan]{i}. Relevance: {result.score:.4f}[/bold cyan]")
                console.print(f"   {result.chunk.text}")
                console.print()

            console.print("[yellow]To get LLM-generated answers, implement an LLM provider.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.error("ask_error", error=str(e))
        raise typer.Exit(1)

    # Cleanup
    await embedding_provider.close()
    await metadata_store.close()
    await vector_store.close()


# Repository management subcommand group
repo_app = typer.Typer(help="Manage repositories")
app.add_typer(repo_app, name="repo")


@repo_app.command("create")
def repo_create(
    name: str = typer.Argument(..., help="Repository name (kebab-case)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Repository description"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Create a new repository."""
    asyncio.run(_repo_create_async(name, description, config_file))


async def _repo_create_async(name: str, description: Optional[str], config_file: Optional[Path]):
    """Async implementation of repo create command."""
    config = _load_config(config_file)

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Create repository manager
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)

    try:
        # Check if repository already exists
        existing = await repo_manager.get_repository_by_name(name)
        if existing:
            console.print(f"[red]Repository '{name}' already exists[/red]")
            raise typer.Exit(1)

        # Create new repository
        repository = await repo_manager.create_repository(
            name=name,
            description=description,
        )

        console.print(f"[green]✓[/green] Created repository: {repository.name}")
        console.print(f"  ID: {repository.id}")
        if repository.description:
            console.print(f"  Description: {repository.description}")

    except Exception as e:
        console.print(f"[red]Error creating repository: {str(e)}[/red]")
        raise typer.Exit(1)

    # Cleanup
    await metadata_store.close()
    await vector_store.close()


@repo_app.command("list")
def repo_list(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """List all repositories."""
    asyncio.run(_repo_list_async(config_file))


async def _repo_list_async(config_file: Optional[Path]):
    """Async implementation of repo list command."""
    config = _load_config(config_file)

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Create repository manager
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)

    try:
        # List all repositories
        repositories = await repo_manager.list_repositories()

        if not repositories:
            console.print("[yellow]No repositories found[/yellow]")
        else:
            table = Table(title="Repositories")
            table.add_column("Name", style="cyan")
            table.add_column("ID", style="dim")
            table.add_column("Description", style="green")
            table.add_column("Documents", style="yellow")

            for repo in repositories:
                # Count documents in this repository
                docs = await metadata_store.list_documents(repository_id=repo.id)
                doc_count = len(docs)

                table.add_row(
                    repo.name,
                    str(repo.id),
                    repo.description or "-",
                    str(doc_count),
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing repositories: {str(e)}[/red]")
        raise typer.Exit(1)

    # Cleanup
    await metadata_store.close()
    await vector_store.close()


@repo_app.command("info")
def repo_info(
    name: str = typer.Argument(..., help="Repository name"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Show repository information."""
    asyncio.run(_repo_info_async(name, config_file))


async def _repo_info_async(name: str, config_file: Optional[Path]):
    """Async implementation of repo info command."""
    config = _load_config(config_file)

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Create repository manager
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)

    try:
        # Get repository
        repository = await repo_manager.get_repository_by_name(name)

        if not repository:
            console.print(f"[red]Repository '{name}' not found[/red]")
            raise typer.Exit(1)

        # Get statistics
        docs = await metadata_store.list_documents(repository_id=repository.id)
        doc_count = len(docs)
        embedding_count = await vector_store.count()

        # Display info
        table = Table(title=f"Repository: {repository.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("ID", str(repository.id))
        table.add_row("Name", repository.name)
        table.add_row("Description", repository.description or "-")
        table.add_row("Documents", str(doc_count))
        table.add_row("Total Embeddings", str(embedding_count))
        table.add_row("Created", repository.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Updated", repository.updated_at.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting repository info: {str(e)}[/red]")
        raise typer.Exit(1)

    # Cleanup
    await metadata_store.close()
    await vector_store.close()


@repo_app.command("delete")
def repo_delete(
    name: str = typer.Argument(..., help="Repository name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Delete a repository and all its data."""
    asyncio.run(_repo_delete_async(name, force, config_file))


async def _repo_delete_async(name: str, force: bool, config_file: Optional[Path]):
    """Async implementation of repo delete command."""
    config = _load_config(config_file)

    # Confirmation prompt unless --force is used
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete repository '{name}' and all its data?",
            abort=True,
        )

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    # Create repository manager
    from memory.core.repository import RepositoryManager
    repo_manager = RepositoryManager(metadata_store, vector_store)

    try:
        # Get repository
        repository = await repo_manager.get_repository_by_name(name)

        if not repository:
            console.print(f"[red]Repository '{name}' not found[/red]")
            raise typer.Exit(1)

        # Prevent deletion of default repository
        if repository.name == config.default_repository:
            console.print(f"[red]Cannot delete default repository '{name}'[/red]")
            raise typer.Exit(1)

        # Delete repository
        await repo_manager.delete_repository(repository.id)

        console.print(f"[green]✓[/green] Deleted repository: {name}")

    except Exception as e:
        console.print(f"[red]Error deleting repository: {str(e)}[/red]")
        raise typer.Exit(1)

    # Cleanup
    await metadata_store.close()
    await vector_store.close()


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
    table.add_row("Default Repository", config.default_repository)
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
