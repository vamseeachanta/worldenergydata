"""Centralized data path resolution for worldenergydata.

Resolution order:
1. WED_DATA_ROOT environment variable (explicit override)
2. Symlink at <project_root>/data → external mount (convention)
3. Fallback to <project_root>/data/ directory (development)

Usage:
    from worldenergydata.common.data_resolver import get_data_root, get_module_data

    data_root = get_data_root()
    bsee_data = get_module_data("bsee")
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class DataNotFoundError(FileNotFoundError):
    """Raised when data directory cannot be resolved."""


def _get_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


@lru_cache(maxsize=1)
def get_data_root() -> Path:
    """Resolve the data root directory."""
    env_root = os.environ.get("WED_DATA_ROOT")
    if env_root:
        path = Path(env_root)
        if path.is_dir():
            return path
        raise DataNotFoundError(
            f"WED_DATA_ROOT={env_root} is set but directory does not exist"
        )

    project_root = _get_project_root()
    data_dir = project_root / "data"

    if data_dir.is_symlink():
        target = data_dir.resolve()
        if target.is_dir():
            return target
        raise DataNotFoundError(
            f"data/ symlink points to {target} which does not exist"
        )

    if data_dir.is_dir():
        return data_dir

    raise DataNotFoundError(
        f"No data directory found. Options:\n"
        f"  1. Set WED_DATA_ROOT=/path/to/data\n"
        f"  2. Create symlink: ln -s /path/to/data {data_dir}\n"
        f"  3. Create directory: mkdir -p {data_dir}"
    )


def get_module_data(module: str) -> Path:
    """Get the data directory for a specific module."""
    root = get_data_root()
    module_path = root / "modules" / module
    if module_path.is_dir():
        return module_path
    raise DataNotFoundError(
        f"Module data not found: {module} (looked in {module_path})"
    )


def _clear_cache() -> None:
    """Clear the cached data root. Used in tests."""
    get_data_root.cache_clear()
