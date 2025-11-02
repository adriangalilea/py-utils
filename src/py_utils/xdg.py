"""XDG Base Directory Specification.

Exposes XDG base directories respecting environment variables.
https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

Usage:
    from py_utils import xdg

    config_file = xdg.config / "myapp" / "config.toml"
    data_file = xdg.data / "myapp" / "data.db"

TODO: Consider fallbacks if env vars not set
    - Option 1: Use platformdirs dependency
    - Option 2: Bespoke cross-platform implementation to avoid extra dep
    Current: Fails if env vars not set (offensive programming)
"""

import os
from pathlib import Path


class _XDG:
    """XDG base directory paths."""

    @property
    def config(self) -> Path:
        """XDG_CONFIG_HOME - User-specific configuration files.

        Raises:
            RuntimeError: If XDG_CONFIG_HOME is not set
        """
        env_path = os.getenv("XDG_CONFIG_HOME")
        assert env_path, "XDG_CONFIG_HOME not set"
        return Path(env_path)

    @property
    def data(self) -> Path:
        """XDG_DATA_HOME - User-specific data files.

        Raises:
            RuntimeError: If XDG_DATA_HOME is not set
        """
        env_path = os.getenv("XDG_DATA_HOME")
        assert env_path, "XDG_DATA_HOME not set"
        return Path(env_path)

    @property
    def cache(self) -> Path:
        """XDG_CACHE_HOME - User-specific non-essential cached data.

        Raises:
            RuntimeError: If XDG_CACHE_HOME is not set
        """
        env_path = os.getenv("XDG_CACHE_HOME")
        assert env_path, "XDG_CACHE_HOME not set"
        return Path(env_path)

    @property
    def state(self) -> Path:
        """XDG_STATE_HOME - User-specific state files.

        Raises:
            RuntimeError: If XDG_STATE_HOME is not set
        """
        env_path = os.getenv("XDG_STATE_HOME")
        assert env_path, "XDG_STATE_HOME not set"
        return Path(env_path)

    @property
    def runtime(self) -> Path:
        """XDG_RUNTIME_DIR - User-specific runtime files.

        Raises:
            RuntimeError: If XDG_RUNTIME_DIR is not set
        """
        env_path = os.getenv("XDG_RUNTIME_DIR")
        assert env_path, "XDG_RUNTIME_DIR not set"
        return Path(env_path)


# Module-level properties for clean imports
# Usage: from py_utils import xdg; xdg.config
_xdg_instance = _XDG()

config = _xdg_instance.config
data = _xdg_instance.data
cache = _xdg_instance.cache
state = _xdg_instance.state
runtime = _xdg_instance.runtime

__all__ = ["config", "data", "cache", "state", "runtime"]
