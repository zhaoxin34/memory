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

BM25 Hybrid Search:
- ChromaDB >= 1.5.2 supports BM25 sparse embeddings
- Use ChromaBm25EmbeddingFunction for keyword search
- RRF (Reciprocal Rank Fusion) combines vector and BM25 results
"""

import re
from uuid import UUID

import structlog

from memory.entities import Chunk, Embedding, SearchResult
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
        repository_id: UUID | None = None,
        filters: dict | None = None,
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

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        top_k: int = 10,
        repository_id: UUID | None = None,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Hybrid search combining vector similarity and BM25 keyword search.

        Uses RRF (Reciprocal Rank Fusion) to combine results from both methods.

        Args:
            query_text: Original query text for BM25 search
            query_vector: Query embedding vector for vector search
            top_k: Number of results to return
            repository_id: Optional repository ID to filter results
            filters: Optional metadata filters

        Returns:
            List of search results with combined scores

        Raises:
            StorageError: If hybrid search fails
        """
        try:
            # Get config values (defaults if not set)
            vector_weight = 0.7
            bm25_weight = 0.3
            rrf_k = 60

            # Try to get from extra_params if available
            extra_params = self.config.extra_params
            vector_weight = extra_params.get("hybrid_vector_weight", vector_weight)
            bm25_weight = extra_params.get("hybrid_bm25_weight", bm25_weight)
            rrf_k = extra_params.get("hybrid_rrf_k", rrf_k)

            logger.info(
                "hybrid_search_started",
                query_length=len(query_text),
                top_k=top_k,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
                rrf_k=rrf_k,
                repository_id=str(repository_id) if repository_id else "all",
            )

            # Perform vector search and BM25 search in parallel
            import asyncio

            vector_results, bm25_results = await asyncio.gather(
                self.search(query_vector, top_k * 2, repository_id, filters),
                self._bm25_search(query_text, top_k * 2, repository_id, filters),
            )

            # If BM25 returns no results, fall back to pure vector search
            if not bm25_results:
                logger.warning(
                    "bm25_search_returned_no_results_falling_back_to_vector",
                    vector_results_count=len(vector_results),
                )
                vector_results.sort(key=lambda x: x.score, reverse=True)
                return vector_results[:top_k]

            # Apply RRF fusion
            fused_results = self._rrf_fusion(
                vector_results,
                bm25_results,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
                rrf_k=rrf_k,
            )

            # Sort by score and limit to top_k
            fused_results.sort(key=lambda x: x.score, reverse=True)
            fused_results = fused_results[:top_k]

            logger.info(
                "hybrid_search_completed",
                results_count=len(fused_results),
                vector_matches=len(vector_results),
                bm25_matches=len(bm25_results),
            )

            return fused_results

        except Exception as e:
            raise StorageError(
                message=f"Failed to perform hybrid search: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    async def _bm25_search(
        self,
        query_text: str,
        top_k: int = 10,
        repository_id: UUID | None = None,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """BM25 keyword search using pure BM25 algorithm.

        This performs a pure keyword-based search without using vector embeddings.

        Args:
            query_text: Query text for BM25 search
            top_k: Number of results to return
            repository_id: Optional repository ID to filter results
            filters: Optional metadata filters

        Returns:
            List of search results with BM25 scores
        """
        try:
            # Determine which collections to search
            if repository_id:
                collections_to_search = [(repository_id, self._get_collection(repository_id))]
            else:
                all_collections = self._client.list_collections()
                collections_to_search = []

                for coll_info in all_collections:
                    name = coll_info.name
                    if name.startswith(self.base_collection_name + "_"):
                        repo_id_str = name[len(self.base_collection_name) + 1:]
                        try:
                            repo_id = UUID(repo_id_str.replace("_", "-"))
                            collection = self._client.get_collection(name)
                            collections_to_search.append((repo_id, collection))
                        except (ValueError, Exception):
                            logger.warning(
                                "skipping_invalid_collection",
                                collection_name=name,
                            )

            results = []

            # Search each collection using BM25
            for repo_id, collection in collections_to_search:
                try:
                    # Get all documents from the collection
                    all_docs = collection.get(include=["documents", "metadatas"])

                    if not all_docs.get("documents"):
                        continue

                    # Compute BM25 scores manually
                    bm25_scores = self._compute_bm25_scores(
                        query_text,
                        all_docs["documents"],
                    )

                    # Get top_k results with non-zero scores
                    scored_docs = [
                        (idx, bm25_scores[idx])
                        for idx in range(len(bm25_scores))
                        if bm25_scores[idx] > 0
                    ]
                    scored_docs.sort(key=lambda x: x[1], reverse=True)

                    for idx, score in scored_docs[:top_k]:
                        metadata = all_docs["metadatas"][idx]
                        document_text = all_docs["documents"][idx]
                        chunk_id_str = all_docs["ids"][idx]

                        chunk = Chunk(
                            id=UUID(chunk_id_str),
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
                            )
                        )

                except Exception as e:
                    logger.warning(
                        "bm25_search_collection_failed",
                        collection=collection.name,
                        error=str(e),
                    )
                    continue

            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)

            logger.info(
                "bm25_search_completed",
                results_count=len(results),
                repository_id=str(repository_id) if repository_id else "all",
            )

            return results

        except ImportError as e:
            raise StorageError(
                message="BM25 search requires chromadb>=1.5.2. Install with: uv sync --extra chroma",
                storage_type="chroma",
                original_error=e,
            )
        except Exception as e:
            raise StorageError(
                message=f"Failed to perform BM25 search: {str(e)}",
                storage_type="chroma",
                original_error=e,
            )

    def _compute_bm25_scores(
        self,
        query: str,
        documents: list[str],
    ) -> list[float]:
        """Compute BM25 scores for query against documents.

        Uses jieba for Chinese tokenization.

        Args:
            query: Query text
            documents: List of documents to score

        Returns:
            List of BM25 scores (0-1 normalized)
        """
        try:
            import math
            from collections import Counter

            import jieba

            if not documents:
                return []

            # Parameters
            k1 = 1.2
            b = 0.75

            # Tokenize query using jieba (handles both Chinese and English)
            query_terms = [w.lower() for w in jieba.lcut(query) if w.strip()]

            if not query_terms:
                return [0.0] * len(documents)

            # Tokenize documents using jieba
            doc_terms_list = [[w.lower() for w in jieba.lcut(doc) if w.strip()] for doc in documents]

            # Calculate average document length
            doc_lengths = [len(terms) for terms in doc_terms_list]
            avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

            # Count total documents
            n_docs = len(documents)

            # Calculate document frequencies for each term
            doc_freqs = {}
            for term in query_terms:
                df = sum(1 for terms in doc_terms_list if term in terms)
                doc_freqs[term] = df

            scores = []
            for doc_terms in doc_terms_list:
                doc_len = max(len(doc_terms), 1)
                doc_term_freq = Counter(doc_terms)

                score = 0.0
                for term in query_terms:
                    if term in doc_term_freq:
                        tf = doc_term_freq[term]
                        df = max(doc_freqs.get(term, 0), 1)

                        # IDF calculation (smoothed)
                        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)

                        # BM25 formula
                        tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_length)))

                        score += idf * tf_component

                scores.append(score)

            # Normalize scores to 0-1 range
            max_score = max(scores) if scores else 1
            if max_score > 0:
                scores = [s / max_score for s in scores]

            return scores

        except ImportError:
            # Fallback to simple tokenization if jieba not available
            import math
            from collections import Counter

            if not documents:
                return []

            k1 = 1.2
            b = 0.75

            query_terms = query.lower().split()
            if not query_terms:
                return [0.0] * len(documents)

            doc_terms_list = [doc.lower().split() for doc in documents]
            doc_lengths = [len(terms) for terms in doc_terms_list]
            avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
            n_docs = len(documents)

            doc_freqs = {}
            for term in query_terms:
                df = sum(1 for terms in doc_terms_list if term in terms)
                doc_freqs[term] = df

            scores = []
            for doc_terms in doc_terms_list:
                doc_len = max(len(doc_terms), 1)
                doc_term_freq = Counter(doc_terms)

                score = 0.0
                for term in query_terms:
                    if term in doc_term_freq:
                        tf = doc_term_freq[term]
                        df = max(doc_freqs.get(term, 0), 1)
                        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
                        tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_length)))
                        score += idf * tf_component

                scores.append(score)

            max_score = max(scores) if scores else 1
            if max_score > 0:
                scores = [s / max_score for s in scores]

            return scores

        except Exception as e:
            logger.warning("bm25_score_computation_failed", error=str(e))
            return [0.0] * len(documents)

    def _rrf_fusion(
        self,
        vector_results: list[SearchResult],
        bm25_results: list[SearchResult],
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        rrf_k: int = 60,
    ) -> list[SearchResult]:
        """Combine vector and BM25 results using RRF (Reciprocal Rank Fusion).

        RRF formula: score = weight * (1 / (k + rank))

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            vector_weight: Weight for vector search results
            bm25_weight: Weight for BM25 search results
            rrf_k: RRF k parameter (default 60)

        Returns:
            Combined and sorted list of search results
        """
        # Build rank maps
        vector_ranks: dict[str, float] = {}
        for rank, result in enumerate(vector_results):
            chunk_id = str(result.chunk.id)
            # RRF score: 1 / (k + rank)
            vector_ranks[chunk_id] = vector_weight * (1.0 / (rrf_k + rank + 1))

        bm25_ranks: dict[str, float] = {}
        for rank, result in enumerate(bm25_results):
            chunk_id = str(result.chunk.id)
            bm25_ranks[chunk_id] = bm25_weight * (1.0 / (rrf_k + rank + 1))

        # Combine scores
        combined_scores: dict[str, float] = {}
        for chunk_id in set(list(vector_ranks.keys()) + list(bm25_ranks.keys())):
            combined_scores[chunk_id] = vector_ranks.get(chunk_id, 0) + bm25_ranks.get(chunk_id, 0)

        # Build result map for quick lookup
        all_results: dict[str, SearchResult] = {}
        for result in vector_results:
            all_results[str(result.chunk.id)] = result
        for result in bm25_results:
            chunk_id = str(result.chunk.id)
            if chunk_id not in all_results:
                all_results[chunk_id] = result

        # Create fused results
        # Use combined RRF score for ranking, but keep original vector score for display
        fused_results = []
        for chunk_id, rrf_score in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True):
            if chunk_id in all_results:
                result = all_results[chunk_id]
                # Use vector search score if available, otherwise use BM25 score
                final_score = result.score if chunk_id in vector_ranks else rrf_score
                fused_results.append(
                    SearchResult(
                        chunk=result.chunk,
                        score=final_score,
                    )
                )

        return fused_results

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
