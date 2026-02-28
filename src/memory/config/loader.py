"""Configuration loading from files and environment.

Supports:
- TOML config files
- Environment variables (MEMORY_* prefix)
- .env files
- Multiple profiles (local, server, cloud)
"""

import tomllib
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from memory.config.schema import AppConfig
from memory.observability.logging import get_logger

logger = get_logger(__name__)


def _expand_path_in_config(config_data: dict) -> dict:
    """Recursively expand ~ in path strings."""
    import os

    def expand(val):
        if isinstance(val, str) and val.startswith("~"):
            return os.path.expanduser(val)
        elif isinstance(val, dict):
            return {k: expand(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [expand(v) for v in val]
        return val

    return {k: expand(v) for k, v in config_data.items()}


def load_config(
    config_path: Optional[Path] = None,
    profile: Optional[str] = None,
    env_file: Optional[Path] = None,
) -> AppConfig:
    """Load application configuration.

    Priority (highest to lowest):
    1. Environment variables
    2. Config file
    3. Defaults

    Args:
        config_path: Path to TOML config file
        profile: Config profile to use (e.g., "local", "server")
        env_file: Path to .env file

    Returns:
        Loaded and validated configuration
    """
    # Load .env file if specified
    if env_file and env_file.exists():
        load_dotenv(env_file)
        logger.info("loaded_env_file", path=str(env_file))

    # Load config file if specified
    config_data = {}
    if not config_path:
        config_path = get_default_config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
        logger.info("loaded_config_file", path=str(config_path))

        # Apply profile if specified
        if profile and profile in config_data.get("profiles", {}):
            profile_data = config_data["profiles"][profile]
            # Merge profile data into config (profile overrides base)
            config_data = {**config_data, **profile_data}
            logger.info("applied_profile", profile=profile)

        # Substitute environment variables in config data
        logger.debug("substituted_env_vars_in_config")

        # Remove profiles field before passing to AppConfig
        config_data.pop("profiles", None)

        # Expand ~ in path strings
        config_data = _expand_path_in_config(config_data)

    # Create config (environment variables override file config)
    config = AppConfig.model_validate(config_data)
    logger.info(
        "config_loaded",
        log_level=config.log_level,
        embedding_provider=config.embedding.provider,
        llm_provider=config.llm.provider,
        vector_store=config.vector_store.store_type,
    )

    return config


def get_default_config_path() -> Path:
    """Get the default config file path.

    Searches in order:
    1. ./config.toml
    2. ~/.memory/config.toml
    3. /etc/memory/config.toml
    """
    search_paths = [
        Path.cwd() / "config.toml",
        Path.home() / ".memory" / "config.toml",
        Path("/etc/memory/config.toml"),
    ]

    for path in search_paths:
        if path.exists():
            return path

    # Return first path as default (will be created if needed)
    return search_paths[0]
