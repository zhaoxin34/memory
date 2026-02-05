"""In-memory storage implementations for testing and development.

These implementations store all data in memory and are useful for:
- Testing without external dependencies
- Development and prototyping
- Small-scale deployments
"""

from typing import Optional
from uuid import UUID

from memory.core.models import Chunk, Document, Embedding, Repository, SearchResult
from memory.storage.base import MetadataStore, StorageConfig, VectorStore


class InMemoryVectorStore(VectorStore):
    """In-memory vector store implementation.

    Stores embeddings in memory with repository-based collection isolation.
    Each repository uses a separate collection: {base_collection}_{repository_name}
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize in-memory vector store."""
        super().__init__(config)
        # Collections organized by repository: {collection_name}_{repo_name} -> list of (embedding, chunk)
        self.collections: dict[str, list[tuple[Embedding, Chunk]]] = {}

    async def initialize(self) -> None:
        """Initialize the vector store."""
        pass

    def _get_collection_name(self, repository_name: str) -> str:
        """Get collection name for a repository."""
        return f"{self.config.collection_name}_{repository_name}"

    async def add_embedding(self, embedding: Embedding, chunk: Chunk) -> None:
        """Store a single embedding with associated chunk metadata."""
        # Get repository name from chunk metadata
        repository_name = chunk.metadata.get("repository_name", "default")
        collection_name = self._get_collection_name(repository_name)

        if collection_name not in self.collections:
            self.collections[collection_name] = []

        self.collections[collection_name].append((embedding, chunk))

    async def add_embeddings_batch(
        self, embeddings: list[Embedding], chunks: list[Chunk]
    ) -> None:
        """Store multiple embeddings in batch."""
        for embedding, chunk in zip(embeddings, chunks):
            await self.add_embedding(embedding, chunk)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        repository_id: Optional[UUID] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search for similar embeddings."""
        # If repository_id is provided, only search in that repository's collection
        if repository_id and filters and "repository_name" in filters:
            repository_name = filters["repository_name"]
            collection_name = self._get_collection_name(repository_name)
            collections_to_search = [collection_name] if collection_name in self.collections else []
        else:
            # Search all collections
            collections_to_search = list(self.collections.keys())

        # Collect all embeddings from target collections
        all_results = []
        for collection_name in collections_to_search:
            for embedding, chunk in self.collections[collection_name]:
                # Simple cosine similarity
                score = self._cosine_similarity(query_vector, embedding.vector)
                all_results.append(SearchResult(chunk=chunk, score=score))

        # Sort by score and return top_k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Delete all embeddings for a document."""
        count = 0
        for collection_name in self.collections:
            original_len = len(self.collections[collection_name])
            self.collections[collection_name] = [
                (emb, chunk)
                for emb, chunk in self.collections[collection_name]
                if chunk.document_id != document_id
            ]
            count += original_len - len(self.collections[collection_name])
        return count

    async def delete_by_chunk_id(self, chunk_id: UUID) -> bool:
        """Delete embedding for a specific chunk."""
        for collection_name in self.collections:
            original_len = len(self.collections[collection_name])
            self.collections[collection_name] = [
                (emb, chunk)
                for emb, chunk in self.collections[collection_name]
                if chunk.id != chunk_id
            ]
            if len(self.collections[collection_name]) < original_len:
                return True
        return False

    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all embeddings for a repository."""
        count = 0
        for collection_name in self.collections:
            original_len = len(self.collections[collection_name])
            self.collections[collection_name] = [
                (emb, chunk)
                for emb, chunk in self.collections[collection_name]
                if chunk.repository_id != repository_id
            ]
            count += original_len - len(self.collections[collection_name])
        return count

    async def count(self) -> int:
        """Return total number of embeddings stored."""
        return sum(len(collection) for collection in self.collections.values())

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        self.collections.clear()


class InMemoryMetadataStore(MetadataStore):
    """In-memory metadata store implementation.

    Stores documents, chunks, and repositories in memory.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize in-memory metadata store."""
        super().__init__(config)
        self.repositories: dict[UUID, Repository] = {}
        self.documents: dict[UUID, Document] = {}
        self.chunks: dict[UUID, Chunk] = {}

    async def initialize(self) -> None:
        """Initialize the metadata store."""
        pass

    async def add_document(self, document: Document) -> None:
        """Store a document."""
        self.documents[document.id] = document

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """Retrieve a document by ID."""
        return self.documents.get(document_id)

    async def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk."""
        self.chunks[chunk.id] = chunk

    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Retrieve a chunk by ID."""
        return self.chunks.get(chunk_id)

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        """Retrieve all chunks for a document."""
        return [chunk for chunk in self.chunks.values() if chunk.document_id == document_id]

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document and its chunks."""
        if document_id not in self.documents:
            return False

        # Delete document
        del self.documents[document_id]

        # Delete associated chunks
        chunk_ids_to_delete = [
            chunk_id for chunk_id, chunk in self.chunks.items() if chunk.document_id == document_id
        ]
        for chunk_id in chunk_ids_to_delete:
            del self.chunks[chunk_id]

        return True

    async def list_documents(
        self, limit: int = 100, offset: int = 0, repository_id: Optional[UUID] = None
    ) -> list[Document]:
        """List documents with pagination."""
        docs = list(self.documents.values())

        # Filter by repository if specified
        if repository_id is not None:
            docs = [doc for doc in docs if doc.repository_id == repository_id]

        # Apply pagination
        return docs[offset : offset + limit]

    async def add_repository(self, repository: Repository) -> None:
        """Store a repository."""
        self.repositories[repository.id] = repository

    async def get_repository(self, repository_id: UUID) -> Optional[Repository]:
        """Retrieve a repository by ID."""
        return self.repositories.get(repository_id)

    async def get_repository_by_name(self, name: str) -> Optional[Repository]:
        """Retrieve a repository by name."""
        for repo in self.repositories.values():
            if repo.name == name:
                return repo
        return None

    async def list_repositories(self) -> list[Repository]:
        """List all repositories."""
        return list(self.repositories.values())

    async def delete_repository(self, repository_id: UUID) -> bool:
        """Delete a repository."""
        if repository_id not in self.repositories:
            return False

        del self.repositories[repository_id]
        return True

    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all documents, chunks, and embeddings for a repository.

        This removes all data associated with a repository while preserving
        the repository itself.

        Args:
            repository_id: Repository ID to clear

        Returns:
            Number of documents deleted
        """
        # Find all documents in the repository
        docs_to_delete = [
            doc_id for doc_id, doc in self.documents.items()
            if doc.repository_id == repository_id
        ]
        doc_count = len(docs_to_delete)

        # Delete all chunks associated with these documents
        chunk_ids_to_delete = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.document_id in docs_to_delete
        ]
        for chunk_id in chunk_ids_to_delete:
            del self.chunks[chunk_id]

        # Also delete any orphaned chunks (shouldn't exist with proper foreign keys)
        orphaned_chunk_ids = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.repository_id == repository_id
        ]
        for chunk_id in orphaned_chunk_ids:
            del self.chunks[chunk_id]

        # Delete the documents
        for doc_id in docs_to_delete:
            del self.documents[doc_id]

        return doc_count

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        self.repositories.clear()
        self.documents.clear()
        self.chunks.clear()
