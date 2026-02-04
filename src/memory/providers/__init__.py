"""Provider abstractions: embeddings and LLM backends."""

from memory.providers.base import EmbeddingProvider, LLMProvider, ProviderConfig, ProviderError


def create_embedding_provider(config: ProviderConfig) -> EmbeddingProvider:
    """Factory function to create embedding providers based on configuration.

    This function dynamically imports and instantiates the appropriate provider
    based on the provider_type in the configuration.

    Args:
        config: Provider configuration with provider_type

    Returns:
        Initialized embedding provider

    Raises:
        ValueError: If provider_type is unknown
        ProviderError: If provider initialization fails or dependencies are missing

    Example:
        config = ProviderConfig(
            provider_type="local",
            model_name="all-MiniLM-L6-v2"
        )
        provider = create_embedding_provider(config)
    """
    provider_type = config.provider_type.lower()

    if provider_type == "local":
        try:
            from memory.providers.local import LocalEmbeddingProvider

            return LocalEmbeddingProvider(config)
        except ImportError as e:
            raise ProviderError(
                message=(
                    "Local embedding provider requires sentence-transformers. "
                    "Install with: uv sync --extra local"
                ),
                provider="local",
                original_error=e,
            )

    elif provider_type == "openai":
        try:
            from memory.providers.openai import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(config)
        except ImportError as e:
            raise ProviderError(
                message=(
                    "OpenAI embedding provider requires openai package. "
                    "Install with: uv sync --extra openai"
                ),
                provider="openai",
                original_error=e,
            )

    else:
        raise ValueError(
            f"Unknown embedding provider type: '{provider_type}'. "
            f"Supported types: local, openai"
        )


__all__ = [
    "EmbeddingProvider",
    "LLMProvider",
    "ProviderConfig",
    "ProviderError",
    "create_embedding_provider",
]
