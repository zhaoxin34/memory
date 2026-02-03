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

from pathlib import Path
from typing import Optional
from uuid import UUID

from memory.config.schema import AppConfig
from memory.core.chunking import create_chunks
from memory.core.models import Document, DocumentType, Embedding
from memory.observability.logging import get_logger
from memory.providers.base import EmbeddingProvider
from memory.storage.base import MetadataStore, VectorStore

logger = get_logger(__name__)


class IngestionPipeline:
    """Pipeline for ingesting documents into the knowledge base."""

    def __init__(
        self,
        config: AppConfig,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
    ):
        """Initialize the ingestion pipeline.

        Args:
            config: Application configuration
            embedding_provider: Provider for generating embeddings
            vector_store: Storage for embeddings
            metadata_store: Storage for documents and chunks
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.metadata_store = metadata_store

    async def ingest_document(self, document: Document) -> int:
        """Ingest a single document.

        Args:
            document: Document to ingest

        Returns:
            Number of chunks created

        Raises:
            IngestionError: If ingestion fails
        """
        logger.info("ingestion_started", document_id=str(document.id), source=document.source_path)

        try:
            # Store document metadata
            await self.metadata_store.add_document(document)

            # Create chunks
            chunks = create_chunks(document, self.config.chunking)
            if not chunks:
                logger.warning("no_chunks_created", document_id=str(document.id))
                return 0

            # Store chunks
            for chunk in chunks:
                await self.metadata_store.add_chunk(chunk)

            # Generate embeddings in batches
            batch_size = self.config.embedding.batch_size
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                texts = [chunk.content for chunk in batch]

                # Generate embeddings
                vectors = await self.embedding_provider.embed_batch(texts)

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
                await self.vector_store.add_embeddings_batch(embeddings, batch)

            logger.info(
                "ingestion_completed",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            return len(chunks)

        except Exception as e:
            logger.error(
                "ingestion_failed",
                document_id=str(document.id),
                error=str(e),
            )
            raise IngestionError(f"Failed to ingest document: {e}") from e

    async def ingest_file(self, file_path: Path) -> UUID:
        """Ingest a file from the filesystem.

        Args:
            file_path: Path to file

        Returns:
            Document ID

        Raises:
            IngestionError: If file cannot be read or ingested
        """
        if not file_path.exists():
            raise IngestionError(f"File not found: {file_path}")

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise IngestionError(f"Failed to read file: {e}") from e

        # Determine document type
        doc_type = self._detect_document_type(file_path)

        # Create document
        document = Document(
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
