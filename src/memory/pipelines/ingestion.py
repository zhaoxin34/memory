"""Ingestion pipeline: load, chunk, embed, and store documents.

Why this exists:
- Orchestrates the full document ingestion flow
- Handles batch processing efficiently
- Provides progress tracking and error handling

How to use:
    from memory.pipelines.ingestion import IngestionPipeline

    pipeline = IngestionPipeline(config, embedding_provider, vector_store, metadata_store)
    await pipeline.ingest_document(document)
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from memory.config.schema import AppConfig
from memory.core.chunking import create_chunks
from memory.core.models import Document, DocumentType, Embedding
from memory.observability.logging import get_logger
from memory.providers.base import EmbeddingProvider
from memory.storage.base import MetadataStore, VectorStore

logger = get_logger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    chunk_count: int
    updated: bool
    reason: str | None = None
    document_id: UUID | None = None


class IngestionPipeline:
    """Pipeline for ingesting documents into the knowledge base."""

    def __init__(
        self,
        config: AppConfig,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        repository_id: UUID | None = None,
    ):
        """Initialize the ingestion pipeline.

        Args:
            config: Application configuration
            embedding_provider: Provider for generating embeddings
            vector_store: Storage for embeddings
            metadata_store: Storage for documents and chunks
            repository_id: Optional repository ID for document isolation
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.repository_id = repository_id

    async def ingest_document(self, document: Document, force: bool = False) -> IngestionResult:
        """Ingest a single document.

        Args:
            document: Document to ingest
            force: If True, re-import even if content hasn't changed

        Returns:
            IngestionResult with chunk count and update status

        Raises:
            IngestionError: If ingestion fails
        """
        logger.info("ingestion_started", document_id=str(document.id), source=document.source_path, force=force)

        # Store original document for rollback if needed
        original_document = None
        original_chunks = None

        try:
            # Find existing document by source_path and repository_id
            logger.info("finding_document_by_source_path", source_path=document.source_path, repository_id=str(document.repository_id))
            existing_doc = await self._find_document_by_source_path(
                document.source_path,
                document.repository_id
            )

            # Initialize variables for document replacement tracking
            original_document = None
            content_changed = False

            if existing_doc:
                logger.info("existing_document_found", document_id=str(existing_doc.id), existing_md5=existing_doc.content_md5, new_md5=document.content_md5)
                # Check if content has changed based on MD5
                content_changed = (
                    existing_doc.content_md5 != document.content_md5 or
                    existing_doc.content_md5 is None or
                    document.content_md5 is None
                )

                if not content_changed and not force:
                    # Content hasn't changed and not forcing, skip ingestion
                    existing_chunks = await self.metadata_store.get_chunks_by_document(existing_doc.id)
                    logger.info("content_unchanged",
                               document_id=str(existing_doc.id),
                               source=document.source_path)
                    return IngestionResult(
                        chunk_count=len(existing_chunks),
                        updated=False,
                        reason="content_unchanged",
                        document_id=existing_doc.id
                    )

                # Content has changed or force is True
                logger.info("content_changed_or_forced",
                           document_id=str(document.id),
                           source=document.source_path,
                           content_changed=content_changed,
                           force=force)

                # Store for rollback
                original_document = existing_doc
                original_chunks = await self.metadata_store.get_chunks_by_document(existing_doc.id)

                # Delete existing document and associated data
                await self._delete_document_cascade(existing_doc.id)
                logger.info("deleted_existing_document", original_id=str(existing_doc.id))
            else:
                logger.info("no_existing_document_found", source_path=document.source_path)

            # Store document metadata
            logger.info("storing_document_metadata", document_id=str(document.id))
            await self.metadata_store.add_document(document)
            logger.info("document_metadata_stored", document_id=str(document.id))

            # Create chunks
            logger.info("creating_chunks", document_id=str(document.id))
            chunks = create_chunks(document, self.config.chunking)
            logger.info("chunks_created", document_id=str(document.id), chunk_count=len(chunks))
            if not chunks:
                logger.warning("no_chunks_created", document_id=str(document.id))
                return IngestionResult(
                    chunk_count=0,
                    updated=False,
                    reason="no_chunks_created",
                    document_id=document.id
                )

            # Store chunks
            logger.info("storing_chunks", document_id=str(document.id), chunk_count=len(chunks))
            for i, chunk in enumerate(chunks):
                logger.debug(
                    "storing_chunk",
                    document_id=str(document.id),
                    chunk_index=i,
                    chunk_id=str(chunk.id),
                )
                await self.metadata_store.add_chunk(chunk)
            logger.info("chunks_stored", document_id=str(document.id), chunk_count=len(chunks))

            # Generate embeddings in batches
            batch_size = self.config.embedding.batch_size
            logger.info(
                "generating_embeddings",
                document_id=str(document.id),
                batch_size=batch_size,
                total_chunks=len(chunks),
            )
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(chunks) + batch_size - 1) // batch_size
                texts = [chunk.content for chunk in batch]

                logger.info(
                    "processing_embedding_batch",
                    document_id=str(document.id),
                    batch_num=batch_num,
                    total_batches=total_batches,
                    batch_size=len(batch),
                )
                # Generate embeddings
                vectors = await self.embedding_provider.embed_batch(texts)
                logger.info(
                    "embeddings_generated",
                    document_id=str(document.id),
                    batch_num=batch_num,
                    vector_count=len(vectors),
                )

                # Create embedding objects
                embeddings = [
                    Embedding(
                        chunk_id=chunk.id,
                        vector=vector,
                        model=self.config.embedding.model_name,
                        dimension=len(vector),
                    )
                    for chunk, vector in zip(batch, vectors)
                ]

                # Store embeddings
                logger.info(
                    "storing_embeddings",
                    document_id=str(document.id),
                    batch_num=batch_num,
                    embedding_count=len(embeddings),
                )
                await self.vector_store.add_embeddings_batch(embeddings, batch)
                logger.info("embeddings_stored", document_id=str(document.id), batch_num=batch_num)

            logger.info(
                "ingestion_completed",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            # Determine reason for update
            reason = None
            if original_document:
                if content_changed:
                    reason = "content_changed"
                else:
                    reason = "forced"

            return IngestionResult(
                chunk_count=len(chunks),
                updated=original_document is not None or reason == "new_document",
                reason=reason if reason else "new_document",
                document_id=document.id
            )

        except Exception as e:
            logger.error(
                "ingestion_failed",
                document_id=str(document.id),
                error=str(e),
            )

            # Attempt rollback if we overwrote an existing document
            if original_document:
                logger.warning("attempting_rollback_after_failure",
                             original_id=str(original_document.id))
                try:
                    # Delete the new document we tried to create
                    await self._delete_document_cascade(document.id)

                    # Restore the original document
                    await self.metadata_store.add_document(original_document)
                    for chunk in original_chunks:
                        await self.metadata_store.add_chunk(chunk)

                    logger.info("rollback_successful", original_id=str(original_document.id))
                except Exception as rollback_error:
                    logger.error(
                        "rollback_failed",
                        original_id=str(original_document.id),
                        error=str(rollback_error),
                    )

            raise IngestionError(f"Failed to ingest document: {e}") from e

    async def _find_document_by_source_path(self, source_path: str, repository_id: UUID) -> Document | None:
        """Find a document by its source path and repository ID.

        Args:
            source_path: Source path to search for
            repository_id: Repository ID to search in

        Returns:
            Document if found, None otherwise
        """
        logger.debug("finding_document_by_source_path", source_path=source_path, repository_id=str(repository_id))

        # List all documents in the repository
        documents = await self.metadata_store.list_documents(repository_id=repository_id, limit=10000)

        # Find document with matching source path
        for doc in documents:
            if doc.source_path == source_path:
                logger.debug("found_existing_document", document_id=str(doc.id), source_path=source_path)
                return doc

        logger.debug("no_existing_document_found", source_path=source_path, repository_id=str(repository_id))
        return None

    async def _delete_document_cascade(self, document_id: UUID) -> None:
        """Delete a document and all its associated data (chunks and embeddings).

        Args:
            document_id: ID of document to delete
        """
        logger.info("cascade_delete_started", document_id=str(document_id))

        # Delete embeddings from vector store first
        try:
            await self.vector_store.delete_by_document_id(document_id)
            logger.info("deleted_embeddings", document_id=str(document_id))
        except Exception as e:
            logger.warning("failed_to_delete_embeddings", document_id=str(document_id), error=str(e))

        # Delete document and chunks from metadata store
        await self.metadata_store.delete_document(document_id)
        logger.info("cascade_delete_completed", document_id=str(document_id))

    async def ingest_file(self, file_path: Path, repository_id: UUID | None = None) -> UUID:
        """Ingest a file from the filesystem.

        Args:
            file_path: Path to file
            repository_id: Optional repository ID (overrides pipeline default)

        Returns:
            Document ID

        Raises:
            IngestionError: If file cannot be read or ingested
        """
        if not file_path.exists():
            raise IngestionError(f"File not found: {file_path}")

        # Use provided repository_id or fall back to pipeline default
        repo_id = repository_id or self.repository_id
        if not repo_id:
            raise IngestionError("repository_id is required but not provided")

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise IngestionError(f"Failed to read file: {e}") from e

        # Determine document type
        doc_type = self._detect_document_type(file_path)

        # Create document
        document = Document(
            repository_id=repo_id,
            source_path=str(file_path),
            doc_type=doc_type,
            title=file_path.stem,
            content=content,
            metadata={"file_size": file_path.stat().st_size},
        )

        await self.ingest_document(document)
        return document.id

    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from file extension."""
        suffix = file_path.suffix.lower()
        type_map = {
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".txt": DocumentType.TEXT,
            ".pdf": DocumentType.PDF,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
        }
        return type_map.get(suffix, DocumentType.UNKNOWN)


class IngestionError(Exception):
    """Exception raised during document ingestion."""

    pass
