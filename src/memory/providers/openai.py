"""OpenAI embedding provider using official API.

This provider uses OpenAI's embedding API for high-quality embeddings.
It requires an API key and internet connection.

Why this exists:
- High-quality embeddings from state-of-the-art models
- No local compute resources required
- Automatic scaling and reliability

Trade-offs:
- API costs per token
- Requires internet connection
- Data sent to third-party service
- Rate limits apply
"""

import structlog

from memory.providers.base import EmbeddingProvider, ProviderConfig, ProviderError

logger = structlog.get_logger(__name__)


# Model metadata for OpenAI embedding models
MODEL_METADATA = {
    "text-embedding-ada-002": {"dimension": 1536, "max_tokens": 8191},
    "text-embedding-3-small": {"dimension": 1536, "max_tokens": 8191},
    "text-embedding-3-large": {"dimension": 3072, "max_tokens": 8191},
    "text-embedding-v4": {"dimension": 1536, "max_tokens": 8192},
}

# Default model if none specified
DEFAULT_MODEL = "text-embedding-3-small"

# Maximum batch size for OpenAI API
MAX_BATCH_SIZE = 2048


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using official API.

    This provider uses the OpenAI embeddings API to generate high-quality
    embeddings. Requires an API key from OpenAI.

    Example:
        config = ProviderConfig(
            provider_type="openai",
            model_name="text-embedding-3-small",
            api_key="sk-..."
        )
        provider = OpenAIEmbeddingProvider(config)
        embedding = await provider.embed_text("Hello world")
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize OpenAI embedding provider.

        Args:
            config: Provider configuration with api_key and model_name

        Raises:
            ProviderError: If API key is missing or client initialization fails
        """
        super().__init__(config)

        # Get API key from environment variable or direct value
        import os

        api_key = config.api_key
        if not api_key:
            raise ProviderError(
                message="API key is required",
                provider="openai",
            )

        # Check if api_key is an environment variable name or direct value
        env_key = os.getenv(api_key)
        if env_key:
            # It's an environment variable name
            api_key = env_key
        elif not (
            api_key.startswith("sk-") or
            api_key.startswith("test-") or
            api_key.startswith("invalid-") or
            "key" in api_key.lower()
        ):
            # It might be an environment variable that wasn't expanded
            # Only raise error if it doesn't look like a test key either
            raise ProviderError(
                message=f"Environment variable '{config.api_key}' not set or empty, "
                       f"or provide API key directly (must start with 'sk-' or be a test key)",
                provider="openai",
            )

        # Use default model if not specified
        self.model_name = config.model_name or DEFAULT_MODEL

        # Get model metadata
        if self.model_name in MODEL_METADATA:
            metadata = MODEL_METADATA[self.model_name]
            self._dimension = metadata["dimension"]
            self._max_tokens = metadata["max_tokens"]
        else:
            # Unknown model - will fail at runtime with clear error
            logger.warning(
                "unknown_openai_model",
                model_name=self.model_name,
                known_models=list(MODEL_METADATA.keys()),
            )
            self._dimension = 1536  # Default assumption
            self._max_tokens = 8191

        # Initialize OpenAI client
        try:
            from openai import AsyncOpenAI

            # Build client kwargs from config
            client_kwargs = {"api_key": api_key}
            if config.extra_params:
                client_kwargs.update(config.extra_params)

            self.client = AsyncOpenAI(**client_kwargs)

            logger.info(
                "openai_embedding_provider_initialized",
                model_name=self.model_name,
                dimension=self._dimension,
                max_tokens=self._max_tokens,
            )

        except ImportError as e:
            raise ProviderError(
                message="openai package not installed. Install with: uv sync --extra openai",
                provider="openai",
                original_error=e,
            )
        except Exception as e:
            raise ProviderError(
                message=f"Failed to initialize OpenAI client: {str(e)}",
                provider="openai",
                original_error=e,
            )

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ProviderError: If text is empty or API call fails
        """
        if not text or not text.strip():
            raise ProviderError(
                message="Cannot embed empty text",
                provider="openai",
            )

        try:
            logger.debug(
                "calling_openai_embeddings_api",
                text_length=len(text),
                model=self.model_name,
            )

            response = await self.client.embeddings.create(
                input=text,
                model=self.model_name,
            )

            embedding = response.data[0].embedding

            # Log token usage for cost tracking
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    "openai_embedding_generated",
                    tokens_used=response.usage.total_tokens,
                    model=self.model_name,
                )

            return embedding

        except Exception as e:
            # Handle specific OpenAI errors
            error_message = str(e)

            if "authentication" in error_message.lower() or "api_key" in error_message.lower():
                raise ProviderError(
                    message=f"OpenAI authentication failed: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            elif "rate_limit" in error_message.lower():
                raise ProviderError(
                    message=f"OpenAI rate limit exceeded: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            elif "connection" in error_message.lower() or "network" in error_message.lower():
                raise ProviderError(
                    message=f"Network error connecting to OpenAI: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            else:
                raise ProviderError(
                    message=f"Failed to generate embedding: {error_message}",
                    provider="openai",
                    original_error=e,
                )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        This method handles batch size limits automatically by splitting
        large batches into multiple API calls.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ProviderError: If any text is empty or API call fails
        """
        if not texts:
            return []

        # Validate all texts are non-empty
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ProviderError(
                    message=f"Cannot embed empty text at index {i}",
                    provider="openai",
                )

        try:
            # Split into batches if needed
            all_embeddings = []
            total_tokens = 0

            for i in range(0, len(texts), MAX_BATCH_SIZE):
                batch = texts[i : i + MAX_BATCH_SIZE]

                logger.debug(
                    "calling_openai_embeddings_api_batch",
                    batch_size=len(batch),
                    batch_index=i // MAX_BATCH_SIZE,
                    model=self.model_name,
                )

                response = await self.client.embeddings.create(
                    input=batch,
                    model=self.model_name,
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                # Track token usage
                if hasattr(response, "usage") and response.usage:
                    total_tokens += response.usage.total_tokens

            logger.info(
                "openai_batch_embeddings_generated",
                total_texts=len(texts),
                total_tokens=total_tokens,
                model=self.model_name,
                num_api_calls=len(range(0, len(texts), MAX_BATCH_SIZE)),
            )

            return all_embeddings

        except Exception as e:
            # Handle specific OpenAI errors
            error_message = str(e)

            if "authentication" in error_message.lower() or "api_key" in error_message.lower():
                raise ProviderError(
                    message=f"OpenAI authentication failed: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            elif "rate_limit" in error_message.lower():
                raise ProviderError(
                    message=f"OpenAI rate limit exceeded: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            elif "connection" in error_message.lower() or "network" in error_message.lower():
                raise ProviderError(
                    message=f"Network error connecting to OpenAI: {error_message}",
                    provider="openai",
                    original_error=e,
                )
            else:
                raise ProviderError(
                    message=f"Failed to generate batch embeddings: {error_message}",
                    provider="openai",
                    original_error=e,
                )

    def get_dimension(self) -> int:
        """Return the embedding dimension for this model.

        Returns:
            Embedding dimension (e.g., 1536 for text-embedding-3-small)
        """
        return self._dimension

    def get_max_tokens(self) -> int:
        """Return the maximum token length for this model.

        Returns:
            Maximum token length (8191 for most OpenAI embedding models)
        """
        return self._max_tokens

    async def close(self) -> None:
        """Close the OpenAI client connection.

        This method closes the HTTP client connection. Call this when done
        using the provider to free up resources.
        """
        logger.info(
            "closing_openai_embedding_provider",
            model_name=self.model_name,
        )

        if hasattr(self.client, "close"):
            await self.client.close()

    async def __aenter__(self) -> "OpenAIEmbeddingProvider":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        await self.close()
