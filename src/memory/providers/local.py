"""Local embedding provider using sentence-transformers.

This provider runs embedding models locally without requiring API calls.
It uses the sentence-transformers library for high-quality embeddings.

Why this exists:
- No API costs or rate limits
- Privacy: data never leaves local machine
- Works offline
- Good quality embeddings for most use cases

Trade-offs:
- Requires local compute resources (CPU/GPU)
- Model download required on first use
- May be slower than cloud APIs for large batches
"""

import asyncio
from typing import Optional

import structlog

from memory.providers.base import EmbeddingProvider, ProviderConfig, ProviderError

logger = structlog.get_logger(__name__)


# Model metadata: dimension and max tokens for common models
MODEL_METADATA = {
    "all-MiniLM-L6-v2": {"dimension": 384, "max_tokens": 256},
    "all-mpnet-base-v2": {"dimension": 768, "max_tokens": 384},
    "all-MiniLM-L12-v2": {"dimension": 384, "max_tokens": 256},
    "paraphrase-multilingual-MiniLM-L12-v2": {"dimension": 384, "max_tokens": 128},
    "paraphrase-multilingual-mpnet-base-v2": {"dimension": 768, "max_tokens": 128},
}


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers.

    This provider loads models locally and generates embeddings without
    requiring external API calls. Models are cached after first download.

    Example:
        config = ProviderConfig(
            provider_type="local",
            model_name="all-MiniLM-L6-v2"
        )
        provider = LocalEmbeddingProvider(config)
        embedding = await provider.embed_text("Hello world")
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize local embedding provider.

        Args:
            config: Provider configuration with model_name

        Raises:
            ProviderError: If model loading fails
        """
        super().__init__(config)
        self.model_name = config.model_name
        self._model: Optional[object] = None
        self._dimension: Optional[int] = None
        self._max_tokens: Optional[int] = None

        # Load model synchronously during initialization
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "loading_local_embedding_model",
                model_name=self.model_name,
            )

            self._model = SentenceTransformer(self.model_name)

            # Get model metadata
            if self.model_name in MODEL_METADATA:
                metadata = MODEL_METADATA[self.model_name]
                self._dimension = metadata["dimension"]
                self._max_tokens = metadata["max_tokens"]
            else:
                # Infer dimension from model
                self._dimension = self._model.get_sentence_embedding_dimension()
                # Default max tokens if not in metadata
                self._max_tokens = 512
                logger.warning(
                    "model_metadata_not_found",
                    model_name=self.model_name,
                    inferred_dimension=self._dimension,
                    default_max_tokens=self._max_tokens,
                )

            logger.info(
                "local_embedding_model_loaded",
                model_name=self.model_name,
                dimension=self._dimension,
                max_tokens=self._max_tokens,
            )

        except ImportError as e:
            raise ProviderError(
                message="sentence-transformers not installed. Install with: uv sync --extra local",
                provider="local",
                original_error=e,
            )
        except Exception as e:
            raise ProviderError(
                message=f"Failed to load model '{self.model_name}': {str(e)}",
                provider="local",
                original_error=e,
            )

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ProviderError: If text is empty or embedding generation fails
        """
        if not text or not text.strip():
            raise ProviderError(
                message="Cannot embed empty text",
                provider="local",
            )

        try:
            # Run model inference in thread pool to avoid blocking event loop
            embedding = await asyncio.to_thread(
                self._model.encode,
                text,
                convert_to_numpy=True,
            )

            # Convert numpy array to list
            result = embedding.tolist()

            logger.debug(
                "generated_embedding",
                text_length=len(text),
                embedding_dimension=len(result),
            )

            return result

        except Exception as e:
            raise ProviderError(
                message=f"Failed to generate embedding: {str(e)}",
                provider="local",
                original_error=e,
            )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        This method is more efficient than calling embed_text() multiple times
        as it processes texts in batch mode.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ProviderError: If any text is empty or embedding generation fails
        """
        if not texts:
            return []

        # Validate all texts are non-empty
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ProviderError(
                    message=f"Cannot embed empty text at index {i}",
                    provider="local",
                )

        try:
            logger.debug(
                "generating_batch_embeddings",
                batch_size=len(texts),
            )

            # Run batch inference in thread pool
            embeddings = await asyncio.to_thread(
                self._model.encode,
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            # Convert numpy array to list of lists
            result = embeddings.tolist()

            logger.info(
                "generated_batch_embeddings",
                batch_size=len(texts),
                embedding_dimension=len(result[0]) if result else 0,
            )

            return result

        except Exception as e:
            raise ProviderError(
                message=f"Failed to generate batch embeddings: {str(e)}",
                provider="local",
                original_error=e,
            )

    def get_dimension(self) -> int:
        """Return the embedding dimension for this model.

        Returns:
            Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
        """
        if self._dimension is None:
            raise ProviderError(
                message="Model not initialized",
                provider="local",
            )
        return self._dimension

    def get_max_tokens(self) -> int:
        """Return the maximum token length for this model.

        Returns:
            Maximum token length (e.g., 256 for all-MiniLM-L6-v2)
        """
        if self._max_tokens is None:
            raise ProviderError(
                message="Model not initialized",
                provider="local",
            )
        return self._max_tokens

    async def close(self) -> None:
        """Release model resources.

        This method unloads the model from memory. Call this when done
        using the provider to free up resources.
        """
        if self._model is not None:
            logger.info(
                "closing_local_embedding_provider",
                model_name=self.model_name,
            )
            # sentence-transformers models don't have explicit cleanup
            # but we can release the reference
            self._model = None
            self._dimension = None
            self._max_tokens = None

    async def __aenter__(self) -> "LocalEmbeddingProvider":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        await self.close()
