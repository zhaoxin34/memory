"""Abstract base classes for storage backends.

Why this exists:
- Allows swapping between vector databases (Chroma, Qdrant, FAISS, etc.)
- Separates vector storage from metadata storage
- Enables testing with in-memory implementations

How to extend:
1. Subclass VectorStore or MetadataStore
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from memory.entities import Chunk, Document, Embedding, Repository, SearchResult


class StorageConfig(BaseModel):
    """Base configuration for storage backends."""

    storage_type: str
    connection_string: str | None = None
    collection_name: str = "memory"
    extra_params: dict[str, Any] = {}


class VectorStore(ABC):
    """Abstract interface for vector storage backends.

    Implementations must handle:
    - Storing embeddings with metadata
    - Similarity search
    - Batch operations
    - Index management
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize storage with configuration."""
        self.config = config

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store (create collections, indices, etc.)."""
        pass

    @abstractmethod
    async def add_embedding(self, embedding: Embedding, chunk: Chunk) -> None:
        """Store a single embedding with associated chunk metadata.

        Args:
            embedding: The embedding to store
            chunk: The chunk this embedding represents
        """
        pass

    @abstractmethod
    async def add_embeddings_batch(
        self, embeddings: list[Embedding], chunks: list[Chunk]
    ) -> None:
        """Store multiple embeddings in batch.

        Args:
            embeddings: List of embeddings to store
            chunks: List of chunks corresponding to embeddings
        """
        pass

    @abstractmethod
    async def search(
        self, query_vector: list[float], top_k: int = 10, repository_id: UUID | None = None, filters: dict | None = None
    ) -> list[SearchResult]:
        """Search for similar embeddings.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            repository_id: Optional repository ID to filter results
            filters: Optional metadata filters

        Returns:
            List of search results with scores
        """
        pass

    @abstractmethod
    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Delete all embeddings for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of embeddings deleted
        """
        pass

    @abstractmethod
    async def delete_by_chunk_id(self, chunk_id: UUID) -> bool:
        """Delete embedding for a specific chunk.

        Args:
            chunk_id: Chunk ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all embeddings for a repository.

        Args:
            repository_id: Repository ID to delete

        Returns:
            Number of embeddings deleted
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """Return total number of embeddings stored."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        pass


class MetadataStore(ABC):
    """Abstract interface for metadata storage backends.

    Stores documents and chunks without embeddings.
    Implementations can use SQL, NoSQL, or file-based storage.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize storage with configuration."""
        self.config = config

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the metadata store (create tables, etc.)."""
        pass

    @abstractmethod
    async def add_document(self, document: Document) -> None:
        """Store a document.

        Args:
            document: Document to store
        """
        pass

    @abstractmethod
    async def get_document(self, document_id: UUID) -> Document | None:
        """Retrieve a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document if found, None otherwise
        """
        pass

    @abstractmethod
    async def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk.

        Args:
            chunk: Chunk to store
        """
        pass

    @abstractmethod
    async def get_chunk(self, chunk_id: UUID) -> Chunk | None:
        """Retrieve a chunk by ID.

        Args:
            chunk_id: Chunk ID

        Returns:
            Chunk if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        """Retrieve all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunks
        """
        pass

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document and its chunks.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_documents(self, limit: int = 100, offset: int = 0, repository_id: UUID | None = None) -> list[Document]:
        """List documents with pagination.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            repository_id: Optional repository ID to filter documents

        Returns:
            List of documents
        """
        pass

    @abstractmethod
    async def add_repository(self, repository: Repository) -> None:
        """Store a repository.

        Args:
            repository: Repository to store
        """
        pass

    @abstractmethod
    async def get_repository(self, repository_id: UUID) -> Repository | None:
        """Retrieve a repository by ID.

        Args:
            repository_id: Repository ID

        Returns:
            Repository if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_repository_by_name(self, name: str) -> Repository | None:
        """Retrieve a repository by name.

        Args:
            name: Repository name

        Returns:
            Repository if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_repositories(self) -> list[Repository]:
        """List all repositories.

        Returns:
            List of repositories
        """
        pass

    @abstractmethod
    async def delete_repository(self, repository_id: UUID) -> bool:
        """Delete a repository.

        Args:
            repository_id: Repository ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all documents, chunks, and embeddings for a repository.

        This removes all data associated with a repository while preserving
        the repository itself.

        Args:
            repository_id: Repository ID to clear

        Returns:
            Number of documents deleted

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        pass


class StorageError(Exception):
    """Base exception for storage errors."""

    def __init__(self, message: str, storage_type: str, original_error: Exception | None = None):
        self.message = message
        self.storage_type = storage_type
        self.original_error = original_error
        super().__init__(self.message)
