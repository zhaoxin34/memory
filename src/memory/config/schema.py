"""Configuration schema using Pydantic.

Why this exists:
- Type-safe configuration with validation
- Environment variable support
- Multiple deployment profiles (local, server, cloud)
- Clear documentation of all settings

How to extend:
1. Add new fields to existing config classes
2. Create new config classes for new components
3. Update default.toml with new settings
"""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EmbeddingProviderType(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    LOCAL = "local"
    MOCK = "mock"


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class VectorStoreType(str, Enum):
    """Supported vector stores."""

    CHROMA = "chroma"
    QDRANT = "qdrant"
    FAISS = "faiss"
    MEMORY = "memory"


class MetadataStoreType(str, Enum):
    """Supported metadata stores."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MEMORY = "memory"


class EmbeddingConfig(BaseModel):
    """Embedding provider configuration."""

    provider: EmbeddingProviderType = EmbeddingProviderType.OPENAI
    model_name: str = "text-embedding-ada-002"
    api_key: Optional[str] = None
    batch_size: int = Field(default=32, gt=0)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: LLMProviderType = LLMProviderType.OPENAI
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    max_tokens: int = Field(default=2000, gt=0)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    store_type: VectorStoreType = VectorStoreType.CHROMA
    connection_string: Optional[str] = None
    collection_name: str = "memory"
    persist_directory: Optional[Path] = None
    extra_params: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Expand ~ in paths."""
        if self.persist_directory:
            self.persist_directory = self.persist_directory.expanduser()


class MetadataStoreConfig(BaseModel):
    """Metadata store configuration."""

    store_type: MetadataStoreType = MetadataStoreType.SQLITE
    connection_string: str = "sqlite:///memory.db"
    extra_params: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Expand ~ in connection string."""
        if self.connection_string and "~" in self.connection_string:
            self.connection_string = self.connection_string.replace(
                "~", str(Path.home())
            )


class ChunkingConfig(BaseModel):
    """Document chunking configuration.

    For Markdown documents, these defaults are optimized to preserve semantic structure:
    - chunk_size: 2000 characters (allows full paragraphs + headings)
    - chunk_overlap: 200 characters (maintains context across chunks)
    - min_chunk_size: 200 characters (filters out fragments)
    """

    chunk_size: int = Field(default=2000, gt=0, description="Target chunk size in characters")
    chunk_overlap: int = Field(default=200, ge=0, description="Overlap between chunks in characters")
    min_chunk_size: int = Field(default=200, gt=0, description="Minimum chunk size (smaller chunks are discarded)")


class AppConfig(BaseSettings):
    """Main application configuration.

    Loads from:
    1. Config file (TOML)
    2. Environment variables (prefixed with MEMORY_)
    3. .env file
    """

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "memory"
    log_level: LogLevel = LogLevel.INFO
    json_logs: bool = False
    data_dir: Path = Field(default=Path.home() / ".memory")
    default_repository: str = "default"

    # Component configurations
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    metadata_store: MetadataStoreConfig = Field(default_factory=MetadataStoreConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization: create data directory if needed."""
        # Expand ~ in data_dir
        self.data_dir = self.data_dir.expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
