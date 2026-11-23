"""Source-path bootstrap for standalone scripts in the workspace."""

from __future__ import annotations

import sys
from pathlib import Path


def workspace_source_roots(project_root: Path) -> list[Path]:
    """Return existing roots: project src first, then sorted workspace members."""
    candidates = [project_root / "src", *sorted(project_root.glob("packages/*/src"))]
    return [path for path in candidates if path.is_dir()]


def bootstrap_workspace(project_root: Path) -> None:
    """Prepend workspace source roots without duplicating sys.path entries."""
    for path in reversed(workspace_source_roots(project_root)):
        source_path = str(path)
        if source_path not in sys.path:
            sys.path.insert(0, source_path)
