"""OpenAI LLM Provider implementation.

This module provides an OpenAI-compatible LLM provider using the OpenAI API.
"""

from typing import Any

import httpx

from memory.providers.base import LLMProvider, ProviderConfig, ProviderError


class OpenAILLMProvider(LLMProvider):
    """LLM provider using OpenAI API (or compatible endpoints like Ollama)."""

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the OpenAI LLM provider.

        Args:
            config: Provider configuration with api_key, model_name, etc.
        """
        super().__init__(config)
        self.api_key = config.api_key
        self.model_name = config.model_name
        self.extra_params = config.extra_params

        # Determine base URL (for Ollama compatibility)
        self.base_url = self.extra_params.get("base_url", "https://api.openai.com/v1")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.extra_params.get("timeout", 60.0),
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text completion using OpenAI API.

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
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens

            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            raise ProviderError(
                message=f"OpenAI API error: {e.response.status_code} - {e.response.text}",
                provider="openai",
                original_error=e,
            )
        except Exception as e:
            raise ProviderError(
                message=f"LLM generation failed: {str(e)}",
                provider="openai",
                original_error=e,
            )

    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation).

        For accurate counting, use tiktoken library.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
