"""Storage layer: vector stores and metadata stores."""

from memory.storage.base import (
    MetadataStore,
    StorageConfig,
    StorageError,
    VectorStore,
)


def create_vector_store(config: StorageConfig) -> VectorStore:
    """Factory function to create vector stores based on configuration.

    This function dynamically imports and instantiates the appropriate vector store
    based on the storage_type in the configuration.

    Args:
        config: Storage configuration with storage_type

    Returns:
        Initialized vector store

    Raises:
        ValueError: If storage_type is unknown
        StorageError: If store initialization fails or dependencies are missing

    Example:
        config = StorageConfig(
            storage_type="chroma",
            collection_name="memory",
            extra_params={"persist_directory": "./chroma_db"}
        )
        store = create_vector_store(config)
        await store.initialize()
    """
    storage_type = config.store_type.lower()

    if storage_type == "memory":
        from memory.storage.memory import InMemoryVectorStore

        return InMemoryVectorStore(config)

    elif storage_type == "chroma":
        try:
            from memory.storage.chroma import ChromaVectorStore

            return ChromaVectorStore(config)
        except ImportError as e:
            raise StorageError(
                message=(
                    "Chroma vector store requires chromadb package. "
                    "Install with: uv sync --extra chroma"
                ),
                storage_type="chroma",
                original_error=e,
            )

    else:
        raise ValueError(
            f"Unknown vector store type: '{storage_type}'. "
            f"Supported types: memory, chroma"
        )


def create_metadata_store(config: StorageConfig) -> MetadataStore:
    """Factory function to create metadata stores based on configuration.

    This function dynamically imports and instantiates the appropriate metadata store
    based on the storage_type in the configuration.

    Args:
        config: Storage configuration with storage_type

    Returns:
        Initialized metadata store

    Raises:
        ValueError: If storage_type is unknown
        StorageError: If store initialization fails or dependencies are missing

    Example:
        config = StorageConfig(
            storage_type="memory",
            collection_name="memory"
        )
        store = create_metadata_store(config)
        await store.initialize()
    """
    storage_type = config.store_type.lower()

    if storage_type == "memory":
        from memory.storage.memory import InMemoryMetadataStore

        return InMemoryMetadataStore(config)

    elif storage_type == "sqlite":
        try:
            from memory.storage.sqlite import SQLiteMetadataStore

            return SQLiteMetadataStore(config)
        except ImportError as e:
            raise StorageError(
                message=(
                    "SQLite metadata store requires aiosqlite package. "
                    "Install with: uv add aiosqlite"
                ),
                storage_type="sqlite",
                original_error=e,
            )

    elif storage_type == "chroma":
        # For now, use in-memory metadata store with Chroma vector store
        # In the future, we could implement a persistent metadata store
        from memory.storage.memory import InMemoryMetadataStore

        return InMemoryMetadataStore(config)

    else:
        raise ValueError(
            f"Unknown metadata store type: '{storage_type}'. "
            f"Supported types: memory, sqlite, chroma"
        )


__all__ = [
    "VectorStore",
    "MetadataStore",
    "StorageConfig",
    "StorageError",
    "create_vector_store",
    "create_metadata_store",
]
