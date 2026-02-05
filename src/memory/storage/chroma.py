"""Chroma vector store implementation.

This module provides a persistent vector storage backend using ChromaDB.
Chroma is a lightweight, embedded vector database that stores data locally.

Why this exists:
- Persistent storage without external services
- Lightweight and easy to deploy
- Good performance for small to medium datasets
- Native support for metadata filtering

Trade-offs:
- Not suitable for very large datasets (millions of vectors)
- Single-node only (no distributed mode)
- File-based storage (not as robust as dedicated databases)
"""

import re
from typing import Optional
from uuid import UUID

import structlog

from memory.core.models import Chunk, Embedding, SearchResult
from memory.storage.base import StorageConfig, StorageError, VectorStore

logger = structlog.get_logger(__name__)


def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name for Chroma compatibility.

    Chroma collection names must:
    - Be 3-63 characters long
    - Start and end with alphanumeric
    - Contain only alphanumeric, underscores, or hyphens

    Args:
        name: Original collection name

    Returns:
        Sanitized collection name
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    # Ensure starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "c" + sanitized

    # Ensure ends with alphanumeric
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + "0"

    # Ensure length constraints
    if len(sanitized) < 3:
        sanitized = sanitized + "_default"
    if len(sanitized) > 63:
        sanitized = sanitized[:63]

    return sanitized


class ChromaVectorStore(VectorStore):
    """Chroma vector store implementation.

    This store uses ChromaDB for persistent vector storage. Each repository
    gets its own collection for isolation.

    Example:
        config = StorageConfig(
            storage_type="chroma",
            collection_name="memory",
            extra_params={"persist_directory": "./chroma_db"}
        )
        store = ChromaVectorStore(config)
        await store.initialize()
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize Chroma vector store.

        Args:
            config: Storage configuration

        Raises:
            StorageError: If Chroma initialization fails
        """
        super().__init__(config)

        import os

        # Get persist directory from config and expand user path
        persist_dir = config.extra_params.get("persist_directory", "./chroma_db")
        self.persist_directory = os.path.expanduser(persist_dir)
        self.base_collection_name = config.collection_name

        # Client and collections cache
        self._client = None
        self._collections: dict[str, object] = {}

        logger.info(
            "initializing_chroma_vector_store",
            persist_directory=self.persist_directory,
            base_collection_name=self.base_collection_name,
        )

    async def initialize(self) -> None:
        """Initialize the Chroma client and create persistent storage.

        Raises:
            StorageError: If initialization fails
        """
        try:
            import chromadb

            logger.info(
                "creating_chroma_client",
                persist_directory=self.persist_directory,
            )

            # Create persistent client
            self._client = chromadb.PersistentClient(path=self.persist_directory)

            logger.info("chroma_vector_store_initialized")

        except ImportError as e:
            raise StorageError(
                message="chromadb not installed. Install with: uv sync --extra chroma",
                storage_type="chroma",
                original_error=e,
            )
        except Exception as e:
            raise StorageError(
                message=f"Failed to initialize Chroma client: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    def _get_collection(self, repository_id: UUID) -> object:
        """Get or create a collection for a repository.

        Args:
            repository_id: Repository ID

        Returns:
            Chroma collection object

        Raises:
            StorageError: If collection creation fails
        """
        collection_name = f"{self.base_collection_name}_{str(repository_id)}"
        collection_name = sanitize_collection_name(collection_name)

        if collection_name not in self._collections:
            try:
                logger.debug(
                    "getting_or_creating_collection",
                    collection_name=collection_name,
                    repository_id=str(repository_id),
                )

                collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"repository_id": str(repository_id)},
                )

                self._collections[collection_name] = collection

                logger.info(
                    "collection_ready",
                    collection_name=collection_name,
                    repository_id=str(repository_id),
                )

            except Exception as e:
                raise StorageError(
                    message=f"Failed to get/create collection '{collection_name}': {str(e)}",
                    storage_type="chroma",
                    original_error=e,
                )

        return self._collections[collection_name]

    async def add_embedding(self, embedding: Embedding, chunk: Chunk) -> None:
        """Store a single embedding with associated chunk metadata.

        Args:
            embedding: The embedding to store
            chunk: The chunk this embedding represents

        Raises:
            StorageError: If storage fails
        """
        try:
            collection = self._get_collection(chunk.repository_id)

            # Prepare metadata
            metadata = {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "repository_id": str(chunk.repository_id),
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }

            # Add to collection
            collection.add(
                ids=[str(chunk.id)],
                embeddings=[embedding.vector],
                metadatas=[metadata],
                documents=[chunk.content],
            )

            logger.debug(
                "embedding_added",
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                repository_id=str(chunk.repository_id),
            )

        except Exception as e:
            raise StorageError(
                message=f"Failed to add embedding: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def add_embeddings_batch(
        self, embeddings: list[Embedding], chunks: list[Chunk]
    ) -> None:
        """Store multiple embeddings in batch.

        Args:
            embeddings: List of embeddings to store
            chunks: List of chunks corresponding to embeddings

        Raises:
            StorageError: If batch storage fails
        """
        if not embeddings:
            return

        if len(embeddings) != len(chunks):
            raise StorageError(
                message=f"Embeddings and chunks length mismatch: {len(embeddings)} vs {len(chunks)}",
                storage_type="chroma",
            )

        try:
            # Group by repository
            by_repository: dict[UUID, tuple[list[Embedding], list[Chunk]]] = {}

            for emb, chunk in zip(embeddings, chunks):
                if chunk.repository_id not in by_repository:
                    by_repository[chunk.repository_id] = ([], [])
                by_repository[chunk.repository_id][0].append(emb)
                by_repository[chunk.repository_id][1].append(chunk)

            # Add to each repository's collection
            for repository_id, (repo_embeddings, repo_chunks) in by_repository.items():
                collection = self._get_collection(repository_id)

                # Prepare batch data
                ids = [str(chunk.id) for chunk in repo_chunks]
                vectors = [emb.vector for emb in repo_embeddings]
                metadatas = [
                    {
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "repository_id": str(chunk.repository_id),
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                    for chunk in repo_chunks
                ]
                documents = [chunk.content for chunk in repo_chunks]

                # Add batch to collection
                collection.add(
                    ids=ids,
                    embeddings=vectors,
                    metadatas=metadatas,
                    documents=documents,
                )

                logger.info(
                    "embeddings_batch_added",
                    count=len(repo_chunks),
                    repository_id=str(repository_id),
                )

        except Exception as e:
            raise StorageError(
                message=f"Failed to add embeddings batch: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        repository_id: Optional[UUID] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search for similar embeddings.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            repository_id: Optional repository ID to filter results
            filters: Optional metadata filters

        Returns:
            List of search results with scores

        Raises:
            StorageError: If search fails
        """
        try:
            results = []

            # Determine which collections to search
            if repository_id:
                # Search single repository
                collections_to_search = [(repository_id, self._get_collection(repository_id))]
            else:
                # Search all collections
                all_collections = self._client.list_collections()
                collections_to_search = []

                for coll_info in all_collections:
                    # Extract repository_id from collection name
                    # Format: {base_collection_name}_{repository_id}
                    name = coll_info.name
                    if name.startswith(self.base_collection_name + "_"):
                        repo_id_str = name[len(self.base_collection_name) + 1 :]
                        try:
                            repo_id = UUID(repo_id_str.replace("_", "-"))
                            collection = self._client.get_collection(name)
                            collections_to_search.append((repo_id, collection))
                        except (ValueError, Exception):
                            logger.warning(
                                "skipping_invalid_collection",
                                collection_name=name,
                            )

            # Search each collection
            for repo_id, collection in collections_to_search:
                # Build where clause for filters
                where = {}
                if filters:
                    where.update(filters)

                # Query collection
                query_results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    where=where if where else None,
                )

                # Parse results
                if query_results["ids"] and query_results["ids"][0]:
                    for i, chunk_id_str in enumerate(query_results["ids"][0]):
                        metadata = query_results["metadatas"][0][i]
                        distance = query_results["distances"][0][i]
                        document_text = query_results["documents"][0][i]

                        # Convert distance to similarity score (Chroma uses L2 distance)
                        # Lower distance = higher similarity
                        score = 1.0 / (1.0 + distance)

                        # Create chunk from metadata
                        chunk = Chunk(
                            id=UUID(metadata["chunk_id"]),
                            document_id=UUID(metadata["document_id"]),
                            repository_id=UUID(metadata["repository_id"]),
                            content=document_text,
                            chunk_index=metadata["chunk_index"],
                            start_char=metadata["start_char"],
                            end_char=metadata["end_char"],
                        )

                        results.append(
                            SearchResult(
                                chunk=chunk,
                                score=score,
                                document_id=UUID(metadata["document_id"]),
                            )
                        )

            # Sort by score descending and limit to top_k
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]

            logger.info(
                "search_completed",
                results_count=len(results),
                repository_id=str(repository_id) if repository_id else "all",
            )

            return results

        except Exception as e:
            raise StorageError(
                message=f"Failed to search: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Delete all embeddings for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of embeddings deleted

        Raises:
            StorageError: If deletion fails
        """
        try:
            total_deleted = 0

            # Search all collections
            all_collections = self._client.list_collections()

            for coll_info in all_collections:
                collection = self._client.get_collection(coll_info.name)

                # Query for chunks with this document_id
                results = collection.get(
                    where={"document_id": str(document_id)},
                )

                if results["ids"]:
                    collection.delete(ids=results["ids"])
                    total_deleted += len(results["ids"])

            logger.info(
                "document_embeddings_deleted",
                document_id=str(document_id),
                count=total_deleted,
            )

            return total_deleted

        except Exception as e:
            raise StorageError(
                message=f"Failed to delete by document_id: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def delete_by_chunk_id(self, chunk_id: UUID) -> bool:
        """Delete embedding for a specific chunk.

        Args:
            chunk_id: Chunk ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion fails
        """
        try:
            # Search all collections
            all_collections = self._client.list_collections()

            for coll_info in all_collections:
                collection = self._client.get_collection(coll_info.name)

                try:
                    collection.delete(ids=[str(chunk_id)])
                    logger.info(
                        "chunk_embedding_deleted",
                        chunk_id=str(chunk_id),
                    )
                    return True
                except Exception:
                    # Chunk not in this collection, continue
                    continue

            return False

        except Exception as e:
            raise StorageError(
                message=f"Failed to delete by chunk_id: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all embeddings for a repository.

        Args:
            repository_id: Repository ID to delete

        Returns:
            Number of embeddings deleted

        Raises:
            StorageError: If deletion fails
        """
        try:
            collection_name = f"{self.base_collection_name}_{str(repository_id)}"
            collection_name = sanitize_collection_name(collection_name)

            try:
                collection = self._client.get_collection(collection_name)
                count = collection.count()

                # Delete the entire collection
                self._client.delete_collection(collection_name)

                # Remove from cache
                if collection_name in self._collections:
                    del self._collections[collection_name]

                logger.info(
                    "repository_collection_deleted",
                    repository_id=str(repository_id),
                    count=count,
                )

                return count

            except Exception:
                # Collection doesn't exist
                return 0

        except Exception as e:
            raise StorageError(
                message=f"Failed to delete by repository: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def count(self) -> int:
        """Return total number of embeddings stored.

        Returns:
            Total count across all collections

        Raises:
            StorageError: If count fails
        """
        try:
            total = 0
            all_collections = self._client.list_collections()

            for coll_info in all_collections:
                collection = self._client.get_collection(coll_info.name)
                total += collection.count()

            return total

        except Exception as e:
            raise StorageError(
                message=f"Failed to count embeddings: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def close(self) -> None:
        """Close connections and cleanup resources.

        Chroma automatically persists data, so we just need to clear caches.
        """
        logger.info("closing_chroma_vector_store")

        # Clear collections cache
        self._collections.clear()

        # Chroma client doesn't need explicit cleanup
        self._client = None

    async def __aenter__(self) -> "ChromaVectorStore":
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        await self.close()
