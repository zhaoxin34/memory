"""Command-line interface for the memory knowledge base system.

Commands:
- ingest: Add documents to the knowledge base
- search: Perform semantic search
- ask: Ask questions with LLM-based answers
- chunk: Analyze and display document chunking results
- repo: Manage repositories
- doc: Manage documents (query, info, delete)
- info: Show system information
"""

import asyncio
import datetime as dt
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
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

    # Create stores using factory functions
    try:
        metadata_store = create_metadata_store(config.metadata_store)
        vector_store = create_vector_store(config.vector_store)

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
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing documents with the same source path"),
):
    """Ingest documents into the knowledge base."""
    asyncio.run(_ingest_async(path, config_file, recursive, repository, force))


async def _ingest_async(path: Path, config_file: Optional[Path], recursive: bool, repository: Optional[str], force: bool):
    """Async implementation of ingest command."""
    # Load configuration
    config = _load_config(config_file)

    # Show warning if --force flag is used
    if force:
        console.print("[yellow]WARNING: Using --force flag will overwrite existing documents![/yellow]\n")

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
        return

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
        return

    # Initialize ingestion pipeline
    from memory.pipelines.ingestion import IngestionPipeline

    try:
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
            return

        if not files_to_ingest:
            console.print(f"[yellow]No files found to ingest[/yellow]")
            return

        total_files = len(files_to_ingest)
        console.print(f"[cyan]Ingesting {total_files} file(s) into repository '{repo_name}'...[/cyan]")

        # Ingest each file
        success_count = 0
        error_count = 0
        overwrite_count = 0

        # Use progress bar for multiple files
        if total_files > 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                main_task = progress.add_task(
                    f"Processing {total_files} files...",
                    total=total_files,
                )

                for file_path in files_to_ingest:
                    progress.update(main_task, description=f"Processing: {file_path.name}")

                    try:
                        # Read file content
                        content = file_path.read_text(encoding="utf-8")

                        # Inject filename as heading into content for better embedding
                        filename_title = file_path.stem
                        file_ext = file_path.suffix.lower()

                        # Detect document type and inject filename as heading
                        if file_ext in (".md", ".markdown"):
                            # For markdown files, check if it already has a heading
                            if not content.lstrip().startswith("#"):
                                content = f"# {filename_title}\n\n{content}"
                            doc_type = DocumentType.MARKDOWN
                        else:
                            # For other text files, prepend as first line
                            content = f"# {filename_title}\n\n{content}"
                            doc_type = DocumentType.TEXT

                        # Calculate MD5 hash of content (after injection)
                        import hashlib
                        content_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()

                        # Create document object
                        from memory.core.models import Document, DocumentType

                        document = Document(
                            repository_id=repo.id,
                            source_path=str(file_path),
                            doc_type=doc_type,
                            title=filename_title,
                            content=content,
                            content_md5=content_md5,
                            metadata={"file_size": file_path.stat().st_size},
                        )

                        # Ingest document
                        result = await pipeline.ingest_document(document, force=force)

                        # Check if document was actually updated
                        if result.updated or result.reason == "new_document":
                            if result.reason == "content_changed":
                                overwrite_count += 1
                            elif result.reason == "forced":
                                overwrite_count += 1
                            success_count += 1
                        # Skipped documents don't increment success_count

                    except UnicodeDecodeError:
                        error_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error("ingestion_error", file=str(file_path), error=str(e))

                    progress.advance(main_task)

        else:
            # Single file - keep it simple
            file_path = files_to_ingest[0]
            try:
                console.print(f"  Processing: {file_path}")

                # Read file content
                content = file_path.read_text(encoding="utf-8")

                # Inject filename as heading into content for better embedding
                filename_title = file_path.stem
                file_ext = file_path.suffix.lower()

                # Detect document type and inject filename as heading
                if file_ext in (".md", ".markdown"):
                    # For markdown files, check if it already has a heading
                    if not content.lstrip().startswith("#"):
                        content = f"# {filename_title}\n\n{content}"
                    doc_type = DocumentType.MARKDOWN
                else:
                    # For other text files, prepend as first line
                    content = f"# {filename_title}\n\n{content}"
                    doc_type = DocumentType.TEXT

                # Calculate MD5 hash of content (after injection)
                import hashlib
                content_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()

                # Create document object
                from memory.core.models import Document, DocumentType

                document = Document(
                    repository_id=repo.id,
                    source_path=str(file_path),
                    doc_type=doc_type,
                    title=filename_title,
                    content=content,
                    content_md5=content_md5,
                    metadata={"file_size": file_path.stat().st_size},
                )

                # Ingest document
                result = await pipeline.ingest_document(document, force=force)

                # Check if document was actually updated
                if result.updated or result.reason == "new_document":
                    if result.reason == "content_changed":
                        console.print(f"  [green]✓[/green] Updated (content changed): {file_path.name} ({result.chunk_count} chunks, ID: {result.document_id})")
                        overwrite_count += 1
                        success_count += 1
                    elif result.reason == "forced":
                        console.print(f"  [green]✓[/green] Re-imported (forced): {file_path.name} ({result.chunk_count} chunks, ID: {result.document_id})")
                        overwrite_count += 1
                        success_count += 1
                    elif result.reason == "new_document":
                        console.print(f"  [green]✓[/green] Ingested: {file_path.name} ({result.chunk_count} chunks, ID: {result.document_id})")
                        success_count += 1
                    else:
                        console.print(f"  [green]✓[/green] Ingested: {file_path.name} ({result.chunk_count} chunks, ID: {result.document_id})")
                        success_count += 1
                else:
                    console.print(f"  [dim]→[/dim] Skipped (content unchanged): {file_path.name}")

            except UnicodeDecodeError:
                console.print(f"  [yellow]⚠[/yellow] Skipped (not a text file): {file_path.name}")
                error_count += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] Error: {file_path.name} - {str(e)}")
                error_count += 1
                logger.error("ingestion_error", file=str(file_path), error=str(e))

        # Summary
        console.print()
        if force:
            console.print(f"[green]Successfully processed: {success_count} file(s)[/green]")
            console.print(f"  - Overwritten: {overwrite_count}")
            console.print(f"  - Newly created: {success_count - overwrite_count}")
        else:
            console.print(f"[green]Successfully ingested: {success_count} file(s)[/green]")

        if error_count > 0:
            console.print(f"[yellow]Errors: {error_count} file(s)[/yellow]")

    finally:
        # Cleanup - always execute
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

    # Initialize stores
    metadata_store = None
    vector_store = None
    embedding_provider = None

    try:
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
            return

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

            console.print(f"[cyan]Initializing embedding provider: {config.embedding.provider.value}...[/cyan]")
            embedding_provider = create_embedding_provider(provider_config)
            console.print(f"[green]✓ Embedding provider ready[/green]")

        except Exception as e:
            console.print(f"[red]Error creating embedding provider: {str(e)}[/red]")
            return

        # Perform search directly using vector store
        try:
            console.print(f"[cyan]Searching in repository '{repo_name}'...[/cyan]")

            # Generate query embedding
            console.print("  Generating query embedding...")
            query_vector = await embedding_provider.embed_text(query)
            console.print(f"  ✓ Embedding generated (dimension: {len(query_vector)})")

            # Search in vector store
            console.print("  Searching...")
            results = await vector_store.search(
                query_vector=query_vector,
                top_k=top_k,
                repository_id=repo.id,
            )

            if not results:
                console.print("[yellow]No results found[/yellow]")
            else:
                console.print(f"\n[green]Found {len(results)} result(s):[/green]\n")

                for i, result in enumerate(results, 1):
                    console.print(f"[bold cyan]{i}. Score: {result.score:.4f}[/bold cyan]")
                    console.print(f"   Document ID: {result.chunk.document_id}")
                    console.print(f"   Chunk: {result.chunk.content[:200]}...")
                    console.print()

        except Exception as e:
            console.print(f"[red]Search error: {str(e)}[/red]")
            logger.error("search_error", error=str(e))

    finally:
        # Cleanup - always execute
        if embedding_provider:
            await embedding_provider.close()
        if metadata_store:
            await metadata_store.close()
        if vector_store:
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

    # Note: LLM provider not used in search mode
    llm_provider = None

    pipeline = QueryPipeline(
        config=config,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
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
                console.print(f"   {result.chunk.content}")
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


@app.command()
def chunk(
    source: str = typer.Argument(..., help="Document ID, name, or file path to analyze"),
    size: Optional[int] = typer.Option(None, "--size", help="Custom chunk size in characters"),
    overlap: Optional[int] = typer.Option(None, "--overlap", help="Custom chunk overlap in characters"),
    test_mode: bool = typer.Option(False, "--test", help="Enable test mode (no changes saved)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed chunk information"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name (defaults to config default_repository)"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Analyze and display document chunking results."""
    asyncio.run(_chunk_async(source, size, overlap, test_mode, json_output, verbose, repository, config_file))


async def _chunk_async(
    source: str,
    size: Optional[int],
    overlap: Optional[int],
    test_mode: bool,
    json_output: bool,
    verbose: bool,
    repository: Optional[str],
    config_file: Optional[Path],
):
    """Async implementation of chunk command."""
    from pathlib import Path
    from uuid import UUID
    from typing import Tuple, Optional

    # Load configuration
    config = _load_config(config_file)

    # Validate chunking parameters
    if size is not None and size <= 0:
        console.print("[red]Error: --size must be greater than 0[/red]")
        raise typer.Exit(1)

    if overlap is not None and overlap < 0:
        console.print("[red]Error: --overlap must be greater than or equal to 0[/red]")
        raise typer.Exit(1)

    # Test mode banner
    if test_mode:
        console.print("[cyan]Running in test mode - no changes will be saved[/cyan]\n")

    # Initialize variables
    metadata_store = None
    vector_store = None
    repository_obj = None

    try:
        # Determine repository
        repo_name = repository or config.default_repository

        # Check if source is a file path
        source_path = Path(source)
        is_file_path = source_path.exists()

        if is_file_path:
            # Handle file path input
            console.print(f"[cyan]Analyzing file: {source}[/cyan]\n")

            # Read file content
            try:
                content = source_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                console.print(f"[yellow]Skipping non-text file: {source}[/yellow]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]Error reading file: {str(e)}[/red]")
                raise typer.Exit(1)

            if not content.strip():
                console.print("[yellow]Document is empty, no chunks created[/yellow]")
                raise typer.Exit(0)

            # Create a mock document for chunking
            document_type = "markdown" if source_path.suffix.lower() in ['.md', '.markdown'] else "text"
            doc_metadata = {
                "source_path": str(source_path),
                "file_size": source_path.stat().st_size,
                "document_type": document_type,
            }

        else:
            # Handle repository document input (UUID or name)
            # Ensure default repository exists and get stores
            metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

            # Get the repository object
            from memory.core.repository import RepositoryManager
            repo_manager = RepositoryManager(metadata_store, vector_store)
            repository_obj = await repo_manager.get_repository_by_name(repo_name)

            if not repository_obj:
                console.print(f"[red]Repository '{repo_name}' not found[/red]")
                raise typer.Exit(1)

            console.print(f"[cyan]Analyzing document in repository '{repo_name}'[/cyan]\n")

            # Try to resolve as UUID first
            try:
                doc_uuid = UUID(source)
                document = await metadata_store.get_document(doc_uuid)
                if not document:
                    console.print(f"[red]Document '{source}' not found in repository '{repo_name}'[/red]")
                    raise typer.Exit(1)
            except (ValueError, TypeError):
                # Not a UUID, try as name
                all_docs = await metadata_store.list_documents(repository_id=repository_obj.id)
                matching_docs = [doc for doc in all_docs if (doc.title or doc.source_path) == source]

                if not matching_docs:
                    console.print(f"[red]Document '{source}' not found in repository '{repo_name}'[/red]")
                    raise typer.Exit(1)
                elif len(matching_docs) > 1:
                    console.print(f"[red]Multiple documents match '{source}'. Please use UUID:[/red]")
                    for doc in matching_docs:
                        console.print(f"  - {(doc.title or doc.source_path)}: {doc.id}")
                    raise typer.Exit(1)
                else:
                    document = matching_docs[0]

            content = document.content
            doc_metadata = {
                "document_id": str(document.id),
                "source_path": document.source_path,
                "document_type": document.doc_type.value if document.doc_type else "unknown",
            }

        # Now chunk the content
        content_length = len(content)
        if content_length > 10000:
            console.print(f"[cyan]Chunking document ({content_length} characters)...[/cyan]\n")
        else:
            console.print("[cyan]Chunking document...[/cyan]\n")

        # Create chunking config with overrides
        from memory.config.schema import ChunkingConfig
        from uuid import uuid4
        from memory.core.markdown_chunking import chunk_markdown_document, parse_markdown_sections, smart_merge_chunks
        from memory.core.models import Document as DomainDocument, DocumentType

        chunking_config = ChunkingConfig(
            chunk_size=size if size is not None else config.chunking.chunk_size,
            chunk_overlap=overlap if overlap is not None else config.chunking.chunk_overlap,
        )

        # Perform chunking
        try:
            # For file-based input, create a temporary document with a generated UUID
            if not repository_obj:
                # Generate a temporary UUID for file-based chunking
                temp_repo_id = uuid4()
            else:
                temp_repo_id = repository_obj.id

            # Create a document object for chunking
            domain_doc = DomainDocument(
                repository_id=temp_repo_id,
                source_path=doc_metadata.get("source_path", "unknown"),
                doc_type=DocumentType.TEXT,
                title=doc_metadata.get("source_path", "Document"),
                content=content,
                metadata=doc_metadata,
            )

            # Show progress for large documents
            if content_length > 50000:
                with console.status("[bold green]Processing chunks...[/bold green]"):
                    chunks = chunk_markdown_document(domain_doc, chunking_config)
            else:
                chunks = chunk_markdown_document(domain_doc, chunking_config)
        except Exception as e:
            console.print(f"[red]Error during chunking: {str(e)}[/red]")
            logger.error("chunking_error", error=str(e))
            raise typer.Exit(1)

        if not chunks:
            console.print("[yellow]No chunks were created from this document[/yellow]")
            raise typer.Exit(0)

        # Display results
        console.print(f"[green]✓ Successfully created {len(chunks)} chunks[/green]\n")

        # Display document and repository information
        if is_file_path:
            console.print(f"[bold]Document:[/bold]")
            console.print(f"  Source: {doc_metadata.get('source_path', 'unknown')}")
            console.print(f"  Type: {doc_metadata.get('document_type', 'unknown')}")
            if 'file_size' in doc_metadata:
                console.print(f"  Size: {doc_metadata['file_size']} bytes")
        else:
            console.print(f"[bold]Repository:[/bold]")
            console.print(f"  Name: {repo_name}")
            console.print(f"  ID: {repository_obj.id}")
            console.print(f"\n[bold]Document:[/bold]")
            console.print(f"  ID: {doc_metadata.get('document_id', 'unknown')}")
            console.print(f"  Source: {doc_metadata.get('source_path', 'unknown')}")
            console.print(f"  Type: {doc_metadata.get('document_type', 'unknown')}")
        console.print()

        # Display statistics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        min_size = min(chunk_sizes)
        max_size = max(chunk_sizes)

        # Calculate chunk type distribution
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.get("chunk_type", "unknown")
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

        console.print(f"[bold]Statistics:[/bold]")
        console.print(f"  Total chunks: {len(chunks)}")
        console.print(f"  Average size: {avg_size:.1f} characters")
        console.print(f"  Size range: {min_size} - {max_size} characters")
        console.print(f"  Chunk size used: {chunking_config.chunk_size}")
        console.print(f"  Overlap used: {chunking_config.chunk_overlap}")

        # Display chunk type distribution
        console.print(f"\n[bold]Chunk Types:[/bold]")
        for chunk_type, count in sorted(type_counts.items()):
            percentage = (count / len(chunks)) * 100
            console.print(f"  {chunk_type}: {count} ({percentage:.1f}%)")
        console.print()

        # Display chunks
        if json_output:
            import json
            result = {
                "document": doc_metadata,
                "config": {
                    "chunk_size": chunking_config.chunk_size,
                    "overlap": chunking_config.chunk_overlap,
                },
                "statistics": {
                    "total_chunks": len(chunks),
                    "average_size": avg_size,
                    "min_size": min_size,
                    "max_size": max_size,
                    "type_distribution": type_counts,
                },
                "chunks": [
                    {
                        "index": idx,
                        "type": chunk.metadata.get("chunk_type", "unknown"),
                        "content": chunk.content if verbose else chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                        "size": len(chunk.content),
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                    for idx, chunk in enumerate(chunks)
                ],
            }
            console.print(json.dumps(result, indent=2))
        else:
            # Table output
            table = Table(title="Chunk Analysis Results")
            table.add_column("Index", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta", no_wrap=True)
            table.add_column("Size", style="yellow", no_wrap=True)
            table.add_column("Range", style="blue", no_wrap=True)
            table.add_column("Content Preview", style="green")

            for idx, chunk in enumerate(chunks):
                chunk_type = chunk.metadata.get("chunk_type", "unknown")
                if verbose:
                    # Show more content in verbose mode
                    preview = chunk.content if len(chunk.content) <= 500 else chunk.content[:500] + "..."
                else:
                    preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content

                table.add_row(
                    str(idx),
                    chunk_type,
                    f"{len(chunk.content)} chars",
                    f"{chunk.start_char}-{chunk.end_char}",
                    preview,
                )

            console.print(table)

    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        logger.error("chunk_error", error=str(e))
        raise typer.Exit(1)

    finally:
        # Cleanup
        if metadata_store:
            await metadata_store.close()
        if vector_store:
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
            return

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
        return
    finally:
        # Cleanup - always execute
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
        # Don't raise again, just exit cleanly
        return
    finally:
        # Cleanup - always execute
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
            return

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
        # Convert UTC to local timezone for display
        # Assume stored time is UTC (no timezone info), convert to local
        created_utc = repository.created_at.replace(tzinfo=dt.timezone.utc)
        updated_utc = repository.updated_at.replace(tzinfo=dt.timezone.utc)
        created_local = created_utc.astimezone()
        updated_local = updated_utc.astimezone()
        table.add_row("Created", created_local.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Updated", updated_local.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting repository info: {str(e)}[/red]")
        return
    finally:
        # Cleanup - always execute
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


@repo_app.command("clear")
def repo_clear(
    name: str = typer.Argument(..., help="Repository name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be deleted without actually deleting"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Clear all documents from a repository."""
    asyncio.run(_repo_clear_async(name, dry_run, yes, config_file))


async def _repo_clear_async(name: str, dry_run: bool, yes: bool, config_file: Optional[Path]):
    """Async implementation of repo clear command."""
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

        # Get document count
        docs = await metadata_store.list_documents(repository_id=repository.id)
        doc_count = len(docs)

        # Dry run mode
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/yellow] Would clear {doc_count} documents from '{name}'")
            console.print("[yellow]No changes were made.[/yellow]")
            return

        # Confirmation prompt unless --yes is used
        if not yes:
            console.print(f"\n[bold red]WARNING:[/bold red] This will permanently delete ALL documents")
            console.print(f"from repository '{name}'.\n")

            confirm = typer.confirm("Are you sure you want to continue?", abort=True)

        # Clear repository
        deleted_count = await repo_manager.clear_repository(repository.id)

        console.print(f"\n[green]✓[/green] Successfully cleared {deleted_count} documents")
        console.print(f"  Repository '{name}' is now empty")

    except Exception as e:
        console.print(f"\n[red]✗ Error clearing repository: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
        # Cleanup - always execute
        await metadata_store.close()
        await vector_store.close()


# Document management subcommand group
doc_app = typer.Typer(help="Manage documents")
app.add_typer(doc_app, name="doc")


@doc_app.command("query")
def doc_query(
    page: int = typer.Option(1, "--page", "-p", help="Page number (1-based)"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Number of items per page"),
    search: Optional[str] = typer.Option(None, "--search", help="Search documents by name"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name"),
    sort: str = typer.Option("created_at", "--sort", help="Sort by: created_at, updated_at, name"),
    desc: bool = typer.Option(False, "--desc", help="Sort in descending order"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Query and list documents with pagination and filtering."""
    asyncio.run(_doc_query_async(page, page_size, search, repository, sort, desc, json_output, config_file))


async def _doc_query_async(
    page: int,
    page_size: int,
    search: Optional[str],
    repository: Optional[str],
    sort: str,
    desc: bool,
    json_output: bool,
    config_file: Optional[Path],
):
    """Async implementation of doc query command."""
    # Validate pagination parameters
    if page < 1:
        console.print("[red]Error: Page number must be >= 1[/red]")
        raise typer.Exit(1)

    if page_size < 1:
        console.print("[red]Error: Page size must be > 0[/red]")
        raise typer.Exit(1)

    # Validate sort option
    valid_sort_options = ["created_at", "updated_at", "name"]
    if sort not in valid_sort_options:
        console.print(f"[red]Error: Invalid sort option. Must be one of: {', '.join(valid_sort_options)}[/red]")
        raise typer.Exit(1)

    # Load configuration
    config = _load_config(config_file)

    # Determine repository
    repo_name = repository or config.default_repository

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    try:
        # Get repository
        from memory.core.repository import RepositoryManager
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repo = await repo_manager.get_repository_by_name(repo_name)

        if not repo:
            console.print(f"[red]Repository '{repo_name}' not found[/red]")
            raise typer.Exit(1)

        # List documents with pagination
        # Get all documents with a large limit (pagination in memory)
        all_docs = await metadata_store.list_documents(limit=10000, repository_id=repo.id)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            all_docs = [doc for doc in all_docs if search_lower in (doc.title or "").lower()]

        # Sort documents
        if sort == "created_at":
            all_docs.sort(key=lambda d: d.created_at, reverse=desc)
        elif sort == "updated_at":
            all_docs.sort(key=lambda d: d.updated_at, reverse=desc)
        elif sort == "name":
            all_docs.sort(key=lambda d: (d.title or "").lower(), reverse=desc)

        # Calculate pagination
        total_docs = len(all_docs)
        total_pages = (total_docs + page_size - 1) // page_size

        # Get documents for current page
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_docs)
        page_docs = all_docs[start_idx:end_idx]

        # Get chunk counts for each document
        chunk_counts = {}
        for doc in page_docs:
            chunks = await metadata_store.get_chunks_by_document(doc.id)
            chunk_counts[doc.id] = len(chunks)

        # Output results
        if json_output:
            # JSON output
            import json

            result = {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_documents": total_docs,
                "repository": repo_name,
                "documents": [
                    {
                        "id": str(doc.id),
                        "name": doc.title or doc.source_path,
                        "source_path": doc.source_path,
                        "chunk_count": chunk_counts.get(doc.id, 0),
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    }
                    for doc in page_docs
                ],
            }

            console.print(json.dumps(result, indent=2))
        else:
            # Table output
            if not page_docs:
                console.print(f"[yellow]No documents found{(' matching search criteria' if search else '')} in repository '{repo_name}'[/yellow]")
            else:
                table = Table(title=f"Documents - Repository: {repo_name}")
                table.add_column("ID", style="dim", no_wrap=True)
                table.add_column("Name", style="cyan")
                table.add_column("Source Path", style="green")
                table.add_column("Chunks", style="yellow")
                table.add_column("Created", style="blue")
                table.add_column("Updated", style="magenta")

                for doc in page_docs:
                    table.add_row(
                        str(doc.id),
                        doc.title or doc.source_path,
                        doc.source_path,
                        str(chunk_counts.get(doc.id, 0)),
                        doc.created_at.replace(tzinfo=dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
                        doc.updated_at.replace(tzinfo=dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S") if doc.updated_at else "-",
                    )

                console.print(table)

                # Show pagination info
                if total_pages > 1:
                    console.print(f"\n[dim]Page {page} of {total_pages} (Total: {total_docs} documents)[/dim]")

    except Exception as e:
        console.print(f"[red]Error querying documents: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
        # Cleanup
        await metadata_store.close()
        await vector_store.close()


@doc_app.command("info")
def doc_info(
    document_id: str = typer.Argument(..., help="Document ID (UUID or name)"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name"),
    full: bool = typer.Option(False, "--full", help="Display full content"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Display detailed information about a specific document."""
    asyncio.run(_doc_info_async(document_id, repository, full, json_output, config_file))


async def _doc_info_async(
    document_id: str,
    repository: Optional[str],
    full: bool,
    json_output: bool,
    config_file: Optional[Path],
):
    """Async implementation of doc info command."""
    # Load configuration
    config = _load_config(config_file)

    # Determine repository
    repo_name = repository or config.default_repository

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    try:
        # Get repository
        from memory.core.repository import RepositoryManager
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repo = await repo_manager.get_repository_by_name(repo_name)

        if not repo:
            console.print(f"[red]Repository '{repo_name}' not found[/red]")
            raise typer.Exit(1)

        # Try to resolve document ID (UUID or name)
        from uuid import UUID

        try:
            # Try as UUID first
            doc_uuid = UUID(document_id)
            document = await metadata_store.get_document(doc_uuid)
        except (ValueError, TypeError):
            # Not a UUID, try as name
            all_docs = await metadata_store.list_documents(repository_id=repo.id)
            matching_docs = [doc for doc in all_docs if (doc.title or doc.source_path) == document_id]

            if not matching_docs:
                console.print(f"[red]Document '{document_id}' not found in repository '{repo_name}'[/red]")
                raise typer.Exit(1)
            elif len(matching_docs) > 1:
                console.print(f"[red]Multiple documents match '{document_id}'. Please use UUID:[/red]")
                for doc in matching_docs:
                    console.print(f"  - {(doc.title or doc.source_path)}: {doc.id}")
                raise typer.Exit(1)
            else:
                document = matching_docs[0]

        # Get document chunks for statistics
        from memory.core.models import Chunk
        chunks = await metadata_store.get_chunks_by_document(document.id)

        # Calculate chunk statistics
        chunk_stats = {
            "count": len(chunks),
            "avg_size": sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0,
            "total_size": sum(len(c.content) for c in chunks),
        }

        # Output results
        if json_output:
            # JSON output
            import json

            result = {
                "id": str(document.id),
                "name": document.title or document.source_path,
                "type": document.doc_type.value if document.doc_type else None,
                "source_path": document.source_path,
                "repository_id": str(document.repository_id),
                "repository_name": repo_name,
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                "content_preview": document.content[:500] if not full else document.content,
                "content_length": len(document.content),
                "is_truncated": not full and len(document.content) > 500,
                "chunk_stats": {
                    "count": chunk_stats["count"],
                    "average_size": round(chunk_stats["avg_size"], 2),
                    "total_size": chunk_stats["total_size"],
                },
            }

            console.print(json.dumps(result, indent=2))
        else:
            # Table output
            table = Table(title=f"Document Information: {document.title or document.source_path}")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")

            table.add_row("ID", str(document.id))
            table.add_row("Name", document.title or document.source_path)
            table.add_row("Type", document.doc_type.value if document.doc_type else "-")
            table.add_row("Source Path", document.source_path)
            table.add_row("Repository", repo_name)
            table.add_row("Created", document.created_at.replace(tzinfo=dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S") if document.created_at else "-")
            table.add_row("Updated", document.updated_at.replace(tzinfo=dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S") if document.updated_at else "-")
            table.add_row("Content Length", f"{len(document.content)} characters")
            table.add_row("Total Chunks", str(chunk_stats["count"]))
            table.add_row("Avg Chunk Size", f"{chunk_stats['avg_size']:.2f} chars")

            console.print(table)

            # Content preview
            console.print("\n[bold]Content Preview:[/bold]")
            preview_content = document.content[:500] if not full else document.content
            if len(document.content) > 500 and not full:
                preview_content += "\n... (truncated)"
            console.print(preview_content)

    except Exception as e:
        console.print(f"[red]Error getting document info: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
        # Cleanup
        await metadata_store.close()
        await vector_store.close()


@doc_app.command("delete")
def doc_delete(
    document_ids: list[str] = typer.Argument(..., help="Document ID(s) to delete (UUID or name)"),
    repository: Optional[str] = typer.Option(None, "--repository", help="Repository name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without actually deleting"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Delete one or more documents and all their associated data."""
    asyncio.run(_doc_delete_async(document_ids, repository, force, dry_run, config_file))


async def _doc_delete_async(
    document_ids: list[str],
    repository: Optional[str],
    force: bool,
    dry_run: bool,
    config_file: Optional[Path],
):
    """Async implementation of doc delete command."""
    # Load configuration
    config = _load_config(config_file)

    # Determine repository
    repo_name = repository or config.default_repository

    # Ensure default repository exists and get stores
    metadata_store, vector_store, default_repo = await _ensure_default_repository(config)

    try:
        # Get repository
        from memory.core.repository import RepositoryManager
        repo_manager = RepositoryManager(metadata_store, vector_store)
        repo = await repo_manager.get_repository_by_name(repo_name)

        if not repo:
            console.print(f"[red]Repository '{repo_name}' not found[/red]")
            raise typer.Exit(1)

        # Resolve all document IDs
        from uuid import UUID
        from memory.core.models import Chunk

        documents_to_delete = []
        errors = []

        for doc_id in document_ids:
            try:
                # Try to resolve document ID (UUID or name)
                try:
                    # Try as UUID first
                    doc_uuid = UUID(doc_id)
                    document = await metadata_store.get_document(doc_uuid)
                    if document:
                        documents_to_delete.append(document)
                except (ValueError, TypeError):
                    # Not a UUID, try as name
                    all_docs = await metadata_store.list_documents(repository_id=repo.id)
                    matching_docs = [doc for doc in all_docs if (doc.title or doc.source_path) == doc_id]

                    if not matching_docs:
                        errors.append(f"Document '{doc_id}' not found in repository '{repo_name}'")
                    elif len(matching_docs) > 1:
                        errors.append(f"Multiple documents match '{doc_id}'. Please use UUID:")
                        for doc in matching_docs:
                            errors.append(f"  - {(doc.title or doc.source_path)}: {doc.id}")
                    else:
                        documents_to_delete.append(matching_docs[0])

            except Exception as e:
                errors.append(f"Error resolving document '{doc_id}': {str(e)}")

        # Show errors if any
        if errors:
            for error in errors:
                console.print(f"[red]{error}[/red]")
            if not documents_to_delete:
                raise typer.Exit(1)

        # Dry run mode
        if dry_run:
            console.print("[yellow]Dry run mode - would delete:[/yellow]\n")
            for doc in documents_to_delete:
                # Get chunk count
                chunks = await metadata_store.get_chunks_by_document(doc.id)
                chunk_count = len(chunks)

                # Get embedding count (approximate)
                embedding_count = chunk_count  # Assume one embedding per chunk

                console.print(f"Document: {doc.title or doc.source_path} ({doc.id})")
                console.print(f"  - {chunk_count} chunks")
                console.print(f"  - {embedding_count} embeddings")
                console.print("")

            console.print("[dim]No changes made. Use --force to actually delete.[/dim]")
            return

        # Confirmation prompt if not forced
        if not force:
            if len(documents_to_delete) == 1:
                confirm_msg = f"Are you sure you want to delete document '{documents_to_delete[0].title or documents_to_delete[0].source_path}'? This will remove the document, all chunks, and all embeddings."
            else:
                confirm_msg = f"Are you sure you want to delete {len(documents_to_delete)} documents? This cannot be undone."

            confirm = typer.confirm(confirm_msg, abort=True)

        # Delete documents
        deleted_count = 0
        delete_errors = []

        for document in documents_to_delete:
            try:
                # Get chunks for statistics
                chunks = await metadata_store.get_chunks_by_document(document.id)
                chunk_count = len(chunks)

                # Delete from vector store first
                try:
                    await vector_store.delete_by_document_id(document.id)
                except Exception as e:
                    # Vector store delete might fail if no embeddings exist
                    logger.warning("vector_store_delete_failed", document_id=str(document.id), error=str(e))

                # Delete from metadata store (document and chunks)
                try:
                    await metadata_store.delete_document(document.id)
                except Exception as e:
                    raise Exception(f"Failed to delete document metadata: {str(e)}")

                console.print(f"[green]✓[/green] Deleted document: {document.title or document.source_path} ({chunk_count} chunks removed)")
                deleted_count += 1

            except Exception as e:
                delete_errors.append(f"Failed to delete document '{document.title or document.source_path}': {str(e)}")

        # Show summary
        if delete_errors:
            console.print("\n[yellow]Some deletions encountered errors:[/yellow]")
            for error in delete_errors:
                console.print(f"[red]{error}[/red]")

        console.print(f"\n[green]Successfully deleted {deleted_count} document(s)[/green]")

    except typer.Abort:
        # User cancelled confirmation
        console.print("\n[yellow]Operation cancelled[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error deleting documents: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
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
