"""Unit tests for OpenAIEmbeddingProvider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from memory.providers.openai import OpenAIEmbeddingProvider
from memory.providers.base import ProviderConfig, ProviderError


@pytest.mark.asyncio
class TestOpenAIEmbeddingProvider:
    """Test OpenAIEmbeddingProvider functionality."""

    @patch("openai.AsyncOpenAI")
    async def test_initialization(self, mock_openai_class):
        """Test provider initialization."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        assert provider.config.model_name == "text-embedding-3-small"
        assert provider.config.api_key == "test-key"
        mock_openai_class.assert_called_once_with(api_key="test-key")

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_embed_text(self, mock_openai_class):
        """Test single text embedding."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        text = "This is a test sentence."
        embedding = await provider.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_embed_batch(self, mock_openai_class):
        """Test batch text embedding."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536),
        ]
        mock_response.usage = MagicMock(total_tokens=30)
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
        ]
        embeddings = await provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_embed_empty_text(self, mock_openai_class):
        """Test embedding empty text."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        with pytest.raises(ProviderError):
            await provider.embed_text("")

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_embed_empty_batch(self, mock_openai_class):
        """Test embedding empty batch."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        embeddings = await provider.embed_batch([])
        assert embeddings == []

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_get_dimension(self, mock_openai_class):
        """Test getting embedding dimension."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        dimension = provider.get_dimension()
        assert dimension == 1536

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_get_max_tokens(self, mock_openai_class):
        """Test getting max tokens."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        max_tokens = provider.get_max_tokens()
        assert max_tokens == 8191

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_different_model(self, mock_openai_class):
        """Test using a different model."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-large",
                api_key="test-key",
            )
        )

        assert provider.config.model_name == "text-embedding-3-large"
        dimension = provider.get_dimension()
        assert dimension == 3072

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_context_manager(self, mock_openai_class):
        """Test using provider as context manager."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        async with OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        ) as provider:
            embedding = await provider.embed_text("Test")
            assert len(embedding) == 1536

    @patch("openai.AsyncOpenAI")
    async def test_authentication_error(self, mock_openai_class):
        """Test handling of authentication errors."""
        from openai import AuthenticationError

        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = AuthenticationError(
            "Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="invalid-key",
            )
        )

        with pytest.raises(ProviderError, match="Failed to generate embedding"):
            await provider.embed_text("Test")

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_rate_limit_error(self, mock_openai_class):
        """Test handling of rate limit errors."""
        from openai import RateLimitError

        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        with pytest.raises(ProviderError, match="Rate limit exceeded"):
            await provider.embed_text("Test")

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_api_error(self, mock_openai_class):
        """Test handling of generic API errors."""
        from openai import APIError

        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = APIError(
            "API error",
            request=MagicMock(),
            body=None,
        )
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        with pytest.raises(ProviderError, match="Failed to generate embedding"):
            await provider.embed_text("Test")

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_batch_size_limit(self, mock_openai_class):
        """Test that batches larger than limit are split."""
        mock_client = AsyncMock()

        def create_response_sync(input_texts):
            response = MagicMock()
            response.data = [
                MagicMock(embedding=[0.1] * 1536) for _ in input_texts
            ]
            response.usage = MagicMock(total_tokens=len(input_texts) * 10)
            return response

        async def create_response(**kwargs):
            return create_response_sync(kwargs["input"])

        mock_client.embeddings.create.side_effect = create_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        # Create a batch larger than MAX_BATCH_SIZE (2048)
        texts = [f"Text {i}" for i in range(3000)]

        embeddings = await provider.embed_batch(texts)
        assert len(embeddings) == 3000

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_token_usage_logging(self, mock_openai_class):
        """Test that token usage is logged."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=42)
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
            )
        )

        with patch("memory.providers.openai.logger") as mock_logger:
            await provider.embed_text("Test")

            # Check that token usage was logged
            mock_logger.info.assert_called()
            assert any(
                "tokens_used" in str(call)
                for call in mock_logger.info.call_args_list
            )

        await provider.close()

    @patch("openai.AsyncOpenAI")
    async def test_custom_base_url(self, mock_openai_class):
        """Test initialization with custom base URL."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            ProviderConfig(
                provider_type="openai",
                model_name="text-embedding-3-small",
                api_key="test-key",
                extra_params={"base_url": "https://custom.api.com/v1"},
            )
        )

        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )

        await provider.close()
