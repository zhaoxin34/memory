"""Abstract base classes for embedding and LLM providers.

Why this exists:
- Allows swapping between different embedding models (OpenAI, local, etc.)
- Enables testing with mock providers
- Provides stable interface as providers evolve

How to extend:
1. Subclass EmbeddingProvider or LLMProvider
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """Base configuration for all providers."""

    provider_type: str
    model_name: str
    api_key: Optional[str] = None
    extra_params: dict[str, Any] = {}


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers.

    Implementations must handle:
    - Single text embedding
    - Batch text embedding
    - Model metadata (dimension, max tokens)
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration."""
        self.config = config

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector

        Raises:
            ProviderError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ProviderError: If embedding generation fails
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding dimension for this model."""
        pass

    @abstractmethod
    def get_max_tokens(self) -> int:
        """Return the maximum token length for this model."""
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    Implementations must handle:
    - Text generation with context
    - Streaming responses (optional)
    - Token counting
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration."""
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text

        Raises:
            ProviderError: If generation fails
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for this model."""
        pass


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(self.message)
