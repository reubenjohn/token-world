"""XDG base directory path resolution for Token World.

Follows the XDG Base Directory Specification:
- Data: $XDG_DATA_HOME/token_world (default ~/.local/share/token_world)
- Config: $XDG_CONFIG_HOME/token_world (default ~/.config/token_world)
"""

from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the token_world data directory, respecting XDG_DATA_HOME."""
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(base) / "token_world"


def get_universes_dir() -> Path:
    """Return the universes directory under the data directory."""
    return get_data_dir() / "universes"


def get_config_dir() -> Path:
    """Return the token_world config directory, respecting XDG_CONFIG_HOME."""
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "token_world"
