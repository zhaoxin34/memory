"""Query pipeline: semantic search and LLM-based question answering.

Why this exists:
- Orchestrates the full query flow
- Combines vector search with LLM generation
- Provides both search-only and QA modes

How to use:
    from memory.pipelines.query import QueryPipeline

    pipeline = QueryPipeline(config, embedding_provider, llm_provider, vector_store, metadata_store)
    results = await pipeline.search(query, top_k=5)
    answer = await pipeline.answer(query)
"""

from typing import Optional
from uuid import UUID

from memory.config.schema import AppConfig
from memory.core.models import SearchResult
from memory.observability.logging import get_logger
from memory.providers.base import EmbeddingProvider, LLMProvider
from memory.storage.base import MetadataStore, VectorStore

logger = get_logger(__name__)


class QueryPipeline:
    """Pipeline for querying the knowledge base."""

    def __init__(
        self,
        config: AppConfig,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        repository_id: Optional["UUID"] = None,
    ):
        """Initialize the query pipeline.

        Args:
            config: Application configuration
            embedding_provider: Provider for generating query embeddings
            llm_provider: Provider for generating answers
            vector_store: Storage for embeddings
            metadata_store: Storage for documents and chunks
            repository_id: Optional repository ID for scoped search
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.repository_id = repository_id

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        repository_id: UUID | None = None,
    ) -> list[SearchResult]:
        """Perform semantic search.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            repository_id: Optional repository ID (overrides pipeline default)

        Returns:
            List of search results with scores
        """
        logger.info("search_started", query=query, top_k=top_k)

        # Use provided repository_id or fall back to pipeline default
        repo_id = repository_id or self.repository_id

        # Generate query embedding
        query_vector = await self.embedding_provider.embed_text(query)

        # Search vector store with repository filtering
        results = await self.vector_store.search(
            query_vector, top_k=top_k, repository_id=repo_id, filters=filters
        )

        # Enrich results with document metadata
        for result in results:
            document = await self.metadata_store.get_document(result.chunk.document_id)
            result.document = document

        logger.info("search_completed", query=query, result_count=len(results))

        return results

    async def answer(
        self,
        query: str,
        top_k: int = 5,
        max_context_length: int = 3000,
        repository_id: UUID | None = None,
    ) -> tuple[str, list[SearchResult]]:
        """Answer a question using retrieved context.

        Args:
            query: Question to answer
            top_k: Number of chunks to retrieve
            max_context_length: Maximum context length in characters
            repository_id: Optional repository ID (overrides pipeline default)

        Returns:
            Tuple of (answer, source_chunks)
        """
        logger.info("answer_started", query=query)

        # Retrieve relevant chunks with repository filtering
        results = await self.search(query, top_k=top_k, repository_id=repository_id)

        if not results:
            logger.warning("no_results_found", query=query)
            return "I couldn't find any relevant information to answer your question.", []

        # Build context from top results
        context_parts = []
        total_length = 0

        for result in results:
            chunk_text = result.chunk.content
            if total_length + len(chunk_text) > max_context_length:
                break
            context_parts.append(f"[Source: {result.document.title if result.document else 'Unknown'}]\n{chunk_text}")
            total_length += len(chunk_text)

        context = "\n\n".join(context_parts)

        # Generate answer using LLM
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "If the context doesn't contain enough information to answer the question, say so. "
            "Always cite the sources you use."
        )

        prompt = f"""Context:
{context}

Question: {query}

Answer:"""

        answer = await self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
        )

        logger.info("answer_completed", query=query, source_count=len(context_parts))

        return answer, results[:len(context_parts)]


class QueryError(Exception):
    """Exception raised during query processing."""

    pass
