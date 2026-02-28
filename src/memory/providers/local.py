"""Local embedding provider using sentence-transformers.

This provider runs embedding models locally on the machine.
"""

from memory.providers.base import EmbeddingProvider, ProviderConfig, ProviderError

# Model dimension mappings (for known models)
MODEL_DIMENSIONS = {
    "bge-small-zh-v1.5": 512,
    "bge-base-zh-v1.5": 768,
    "bge-large-zh-v1.5": 1024,
    "bge-m3": 1024,
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
}

# Model max tokens (conservative estimates)
MODEL_MAX_TOKENS = {
    "bge-small-zh-v1.5": 512,
    "bge-base-zh-v1.5": 512,
    "bge-large-zh-v1.5": 512,
    "bge-m3": 8192,
    "all-MiniLM-L6-v2": 256,
    "all-mpnet-base-v2": 384,
}


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers.

    This provider runs embedding models locally, useful for:
    - Offline operation
    - No API costs
    - Privacy-sensitive data

    Example:
        config = ProviderConfig(
            provider_type="local",
            model_name="bge-small-zh-v1.5"
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

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ProviderError(
                message=(
                    "Local embedding provider requires sentence-transformers package. "
                    "Install with: pip install sentence-transformers"
                ),
                provider="local",
                original_error=e,
            )

        model_name = config.model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = self._get_dimension(model_name)
        self._max_tokens = self._get_max_tokens(model_name)

    def _get_dimension(self, model_name: str) -> int:
        """Get embedding dimension for model."""
        # Check known models first
        for known_model, dim in MODEL_DIMENSIONS.items():
            if known_model in model_name or model_name in known_model:
                return dim

        # Try to get from model
        try:
            return self._model.get_sentence_embedding_dimension()
        except Exception:
            # Default fallback
            return 768

    def _get_max_tokens(self, model_name: str) -> int:
        """Get max tokens for model."""
        for known_model, max_tok in MODEL_MAX_TOKENS.items():
            if known_model in model_name or model_name in known_model:
                return max_tok
        return 512

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector

        Raises:
            ProviderError: If embedding generation fails
        """
        try:
            import asyncio

            # Run in thread to avoid blocking
            embedding = await asyncio.to_thread(
                self._model.encode, text, convert_to_numpy=True
            )
            return embedding.tolist()
        except Exception as e:
            raise ProviderError(
                message=f"Failed to generate embedding: {str(e)}",
                provider="local",
                original_error=e,
            )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ProviderError: If embedding generation fails
        """
        try:
            import asyncio

            # Run in thread to avoid blocking
            embeddings = await asyncio.to_thread(
                self._model.encode, texts, convert_to_numpy=True, show_progress_bar=True
            )
            return embeddings.tolist()
        except Exception as e:
            raise ProviderError(
                message=f"Failed to generate batch embeddings: {str(e)}",
                provider="local",
                original_error=e,
            )

    def get_dimension(self) -> int:
        """Return the embedding dimension for this model."""
        return self._dimension

    def get_max_tokens(self) -> int:
        """Return the maximum token length for this model."""
        return self._max_tokens
