"""XDG Base Directory paths.

Reads env vars set by xdg-dirs (https://github.com/adriangalilea/xdg-dirs),
falls back to spec defaults (https://specifications.freedesktop.org/basedir-spec).

Usage:
    from py_utils import xdg

    xdg.config / "myapp" / "config.toml"   # ~/.config/myapp/config.toml
    xdg.data / "myapp" / "data.db"         # ~/.local/share/myapp/data.db
    xdg.state / "notify"                   # ~/.local/state/notify
    xdg.cache / "myapp"                    # ~/.cache/myapp
    xdg.runtime / "myapp"                  # $XDG_RUNTIME_DIR/myapp
"""

import os
from pathlib import Path


def _xdg_dir(env_key: str, fallback: str) -> Path:
    return Path(os.getenv(env_key) or fallback)


_home = Path.home()

config = _xdg_dir("XDG_CONFIG_HOME", str(_home / ".config"))
data = _xdg_dir("XDG_DATA_HOME", str(_home / ".local" / "share"))
state = _xdg_dir("XDG_STATE_HOME", str(_home / ".local" / "state"))
cache = _xdg_dir("XDG_CACHE_HOME", str(_home / ".cache"))
runtime = _xdg_dir("XDG_RUNTIME_DIR", str(_home / ".local" / "run"))

__all__ = ["config", "data", "state", "cache", "runtime"]
