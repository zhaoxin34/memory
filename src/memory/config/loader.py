"""Configuration loading from files and environment.

Supports:
- TOML config files
- Environment variables (MEMORY_* prefix)
- .env files
- Multiple profiles (local, server, cloud)
"""

import os
import re
import tomllib
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from memory.config.schema import AppConfig
from memory.observability.logging import get_logger

logger = get_logger(__name__)


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute environment variables in a data structure.

    Supports formats:
    - ${VAR_NAME}
    - ${VAR_NAME:-default}

    Args:
        obj: Input data (dict, list, str, etc.)

    Returns:
        Data structure with environment variables substituted
    """
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Pattern matches ${VAR_NAME} or ${VAR_NAME:-default}
        def replace_var(match):
            var_expr = match.group(1)
            # Split by :- to separate var name and default value
            if ":-" in var_expr:
                var_name, default_value = var_expr.split(":-", 1)
                return os.getenv(var_name.strip(), default_value)
            else:
                var_name = var_expr.strip()
                value = os.getenv(var_name)
                if value is None:
                    # Return the original if env var not found
                    logger.warning(
                        "env_var_not_found",
                        var_name=var_name,
                        suggestion="Check that the environment variable is set",
                    )
                    return match.group(0)
                return value

        return re.sub(r"\$\{([^}]+)\}", replace_var, obj)
    else:
        return obj


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
    if config_path and config_path.exists():
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
        config_data = _substitute_env_vars(config_data)
        logger.debug("substituted_env_vars_in_config")

        # Remove profiles field before passing to AppConfig
        config_data.pop("profiles", None)

    # Create config (environment variables override file config)
    config = AppConfig(**config_data)
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
