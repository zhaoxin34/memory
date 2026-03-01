"""Store initialization service.

Provides helper functions for initializing storage components.
"""

from memory.config.loader import load_config
from memory.storage import create_metadata_store, create_vector_store


async def initialize_stores(config_path: str | None = None):
    """Initialize metadata store and vector store.

    Args:
        config_path: Optional path to config file

    Returns:
        Tuple of (metadata_store, vector_store)
    """
    config = load_config(config_path=config_path)

    metadata_store = create_metadata_store(config.metadata_store)
    vector_store = create_vector_store(config.vector_store)

    await metadata_store.initialize()
    await vector_store.initialize()

    return metadata_store, vector_store
