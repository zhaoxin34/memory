"""Unit tests for LocalEmbeddingProvider."""

import pytest
from memory.providers.local import LocalEmbeddingProvider
from memory.providers.base import ProviderConfig, ProviderError


@pytest.mark.asyncio
class TestLocalEmbeddingProvider:
    """Test LocalEmbeddingProvider functionality."""

    async def test_initialization(self):
        """Test provider initialization."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)
        assert provider.config.model_name == "all-MiniLM-L6-v2"
        await provider.close()

    async def test_embed_text(self):
        """Test single text embedding."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        text = "This is a test sentence."
        embedding = await provider.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(x, float) for x in embedding)

        await provider.close()

    async def test_embed_batch(self):
        """Test batch text embedding."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
        ]
        embeddings = await provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(x, float) for emb in embeddings for x in emb)

        await provider.close()

    async def test_embed_empty_text(self):
        """Test embedding empty text."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        with pytest.raises(ProviderError):
            await provider.embed_text("")

        await provider.close()

    async def test_embed_empty_batch(self):
        """Test embedding empty batch."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        embeddings = await provider.embed_batch([])
        assert embeddings == []

        await provider.close()

    async def test_get_dimension(self):
        """Test getting embedding dimension."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        dimension = provider.get_dimension()
        assert dimension == 384

        await provider.close()

    async def test_get_max_tokens(self):
        """Test getting max tokens."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        max_tokens = provider.get_max_tokens()
        assert max_tokens == 256

        await provider.close()

    async def test_different_model(self):
        """Test using a different model."""
        config = ProviderConfig(provider_type="local", model_name="all-mpnet-base-v2")
        provider = LocalEmbeddingProvider(config)

        assert provider.config.model_name == "all-mpnet-base-v2"
        dimension = provider.get_dimension()
        assert dimension == 768  # all-mpnet-base-v2 dimension

        await provider.close()

    async def test_context_manager(self):
        """Test using provider as context manager."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        async with LocalEmbeddingProvider(config) as provider:
            embedding = await provider.embed_text("Test")
            assert len(embedding) == 384

    async def test_embedding_consistency(self):
        """Test that same text produces same embedding."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        text = "Consistency test"
        embedding1 = await provider.embed_text(text)
        embedding2 = await provider.embed_text(text)

        # Embeddings should be identical
        assert embedding1 == embedding2

        await provider.close()

    async def test_embedding_similarity(self):
        """Test that similar texts have similar embeddings."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        text1 = "The cat sits on the mat."
        text2 = "A cat is sitting on a mat."
        text3 = "Python is a programming language."

        emb1 = await provider.embed_text(text1)
        emb2 = await provider.embed_text(text2)
        emb3 = await provider.embed_text(text3)

        # Calculate cosine similarity
        def cosine_similarity(a, b):
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot_product / (norm_a * norm_b)

        sim_1_2 = cosine_similarity(emb1, emb2)
        sim_1_3 = cosine_similarity(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_1_2 > sim_1_3
        assert sim_1_2 > 0.7  # High similarity threshold

        await provider.close()

    async def test_long_text_handling(self):
        """Test handling of text longer than max tokens."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        # Create a very long text
        long_text = "word " * 1000

        # Should not raise error, but truncate
        embedding = await provider.embed_text(long_text)
        assert len(embedding) == 384

        await provider.close()

    async def test_special_characters(self):
        """Test handling of special characters."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        texts = [
            "Hello, world!",
            "Test with émojis 😀🎉",
            "中文测试",
            "Mixed 中英文 test",
            "Special chars: @#$%^&*()",
        ]

        embeddings = await provider.embed_batch(texts)
        assert len(embeddings) == len(texts)
        assert all(len(emb) == 384 for emb in embeddings)

        await provider.close()

    async def test_batch_size_handling(self):
        """Test handling of large batches."""
        config = ProviderConfig(provider_type="local", model_name="all-MiniLM-L6-v2")
        provider = LocalEmbeddingProvider(config)

        # Create a large batch
        texts = [f"Sentence number {i}" for i in range(100)]

        embeddings = await provider.embed_batch(texts)
        assert len(embeddings) == 100
        assert all(len(emb) == 384 for emb in embeddings)

        await provider.close()

    async def test_invalid_model_name(self):
        """Test initialization with invalid model name."""
        with pytest.raises(Exception):  # Will raise during model loading
            config = ProviderConfig(provider_type="local", model_name="invalid-model-name")
            provider = LocalEmbeddingProvider(config)
            await provider.embed_text("test")
