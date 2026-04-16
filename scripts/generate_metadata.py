"""Generate per-module freshness metadata (_metadata.json).

Walks ``data/modules/`` and writes a ``_metadata.json`` file in each module
directory summarising file counts, total sizes, format breakdown, and
last-refresh timestamps.

Supports external data roots (e.g. ``/mnt/ace/worldenergydata/data/``)
via ``--external-data-root`` or the ``WED_DATA_ROOT`` env var so that
large binary and raw data hosted outside the repo are included in the
size and file counts.

Usage:
    python scripts/generate_metadata.py
    python scripts/generate_metadata.py --module bsee
    python scripts/generate_metadata.py --external-data-root /mnt/ace/worldenergydata/data
    WED_DATA_ROOT=/mnt/ace/worldenergydata/data python scripts/generate_metadata.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Directories to skip when scanning
_SKIP_DIRS = {
    ".local",
    ".claude-flow",
    "__pycache__",
    "checkpoints",
    "cache",
    ".temp_downloads",
}


def _humanize_bytes(n: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def _should_skip(rel_parts: tuple[str, ...]) -> bool:
    """Return True if a file path should be skipped based on its directory components."""
    return any(p in _SKIP_DIRS or p.startswith(".") for p in rel_parts[:-1])


def scan_directory(dir_path: Path) -> dict[str, Any]:
    """Scan a directory and return file statistics.

    Returns:
        Dict with file_count, total_size_bytes, format_breakdown,
        newest_file, and files list.
    """
    files: list[dict[str, Any]] = []
    format_counts: dict[str, int] = defaultdict(int)
    format_sizes: dict[str, int] = defaultdict(int)
    total_size = 0
    newest_mtime = 0.0

    for fp in sorted(dir_path.rglob("*")):
        if not fp.is_file():
            continue
        try:
            rel = fp.relative_to(dir_path)
        except ValueError:
            continue
        if _should_skip(rel.parts):
            continue

        stat = fp.stat()
        ext = fp.suffix.lower() or "(no ext)"
        format_counts[ext] += 1
        format_sizes[ext] += stat.st_size
        total_size += stat.st_size
        if stat.st_mtime > newest_mtime:
            newest_mtime = stat.st_mtime

        files.append(
            {
                "name": fp.name,
                "path": str(rel),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%d"),
            }
        )

    format_breakdown = {
        ext: {"count": format_counts[ext], "size_bytes": format_sizes[ext]}
        for ext in sorted(format_counts)
    }

    return {
        "file_count": len(files),
        "total_size_bytes": total_size,
        "format_breakdown": format_breakdown,
        "newest_modified": (
            datetime.fromtimestamp(newest_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
            if newest_mtime > 0
            else None
        ),
        "files": files,
    }


def generate_module_metadata(
    module_path: Path,
    module_name: str,
    external_module_path: Path | None = None,
) -> dict[str, Any]:
    """Generate metadata for a single module, merging external data.

    Args:
        module_path: In-repo module directory.
        module_name: Module name (e.g. "bsee").
        external_module_path: Optional external data path for this module.

    Returns:
        Metadata dict ready for JSON serialization.
    """
    scan = scan_directory(module_path)

    # Merge external data if present
    ext_scan = None
    if external_module_path and external_module_path.is_dir():
        if external_module_path.resolve() != module_path.resolve():
            ext_scan = scan_directory(external_module_path)

    if ext_scan:
        # Merge file counts and sizes
        total_files = scan["file_count"] + ext_scan["file_count"]
        total_size = scan["total_size_bytes"] + ext_scan["total_size_bytes"]

        # Merge format breakdowns
        merged_formats: dict[str, dict[str, int]] = {}
        for fmt_dict in (scan["format_breakdown"], ext_scan["format_breakdown"]):
            for ext, info in fmt_dict.items():
                if ext not in merged_formats:
                    merged_formats[ext] = {"count": 0, "size_bytes": 0}
                merged_formats[ext]["count"] += info["count"]
                merged_formats[ext]["size_bytes"] += info["size_bytes"]

        # Merge file lists
        all_files = scan["files"] + [
            {**f, "source": "external"} for f in ext_scan["files"]
        ]

        newest = scan["newest_modified"]
        if ext_scan["newest_modified"]:
            if not newest or ext_scan["newest_modified"] > newest:
                newest = ext_scan["newest_modified"]
    else:
        total_files = scan["file_count"]
        total_size = scan["total_size_bytes"]
        merged_formats = scan["format_breakdown"]
        all_files = scan["files"]
        newest = scan["newest_modified"]

    return {
        "module": module_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_refresh": newest,
        "file_count": total_files,
        "total_size_bytes": total_size,
        "total_size_human": _humanize_bytes(total_size),
        "format_breakdown": dict(sorted(merged_formats.items())),
        "has_external_data": ext_scan is not None,
        "external_data_root": str(external_module_path) if ext_scan else None,
        "files": all_files[:500],  # Cap file listing at 500 entries
        "files_truncated": len(all_files) > 500,
    }


def _resolve_external_root(cli_value: str | None) -> Path | None:
    """Resolve external data root from CLI arg, env var, or auto-detect."""
    path_str = cli_value or os.environ.get("WED_DATA_ROOT")
    if not path_str:
        default = Path("/mnt/ace/worldenergydata/data")
        if default.is_dir():
            return default
        return None
    p = Path(path_str)
    if p.is_dir():
        return p
    print(f"WARNING: external data root not found: {p}", file=sys.stderr)
    return None


def generate_all_metadata(
    root: Path,
    module_filter: str | None = None,
    external_data_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, dict[str, Any]]:
    """Generate metadata for all modules.

    Args:
        root: Project root path.
        module_filter: If set, only process this module.
        external_data_root: Optional external data directory.
        dry_run: If True, do not write files.

    Returns:
        Dict mapping module names to their metadata.
    """
    data_root = root / "data" / "modules"
    ext_modules = external_data_root / "modules" if external_data_root else None

    # Collect module names
    module_names: set[str] = set()
    if data_root.exists():
        for mp in data_root.iterdir():
            if mp.is_dir() and not mp.name.startswith("."):
                module_names.add(mp.name)
    if ext_modules and ext_modules.is_dir():
        for mp in ext_modules.iterdir():
            if mp.is_dir() and not mp.name.startswith("."):
                module_names.add(mp.name)

    results: dict[str, dict[str, Any]] = {}
    written: list[str] = []

    for name in sorted(module_names):
        if module_filter and name != module_filter:
            continue

        mp = data_root / name
        ext_mp = ext_modules / name if ext_modules else None
        if not mp.exists():
            if ext_mp and ext_mp.is_dir():
                mp = ext_mp
                ext_mp = None
            else:
                continue

        metadata = generate_module_metadata(mp, name, external_module_path=ext_mp)
        results[name] = metadata

        if not dry_run:
            out_path = (
                (data_root / name / "_metadata.json")
                if (data_root / name).exists()
                else None
            )
            if out_path:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                try:
                    written.append(str(out_path.relative_to(root)))
                except ValueError:
                    written.append(str(out_path))

    # Print summary
    total_files = sum(m["file_count"] for m in results.values())
    total_size = sum(m["total_size_bytes"] for m in results.values())
    ext_count = sum(1 for m in results.values() if m.get("has_external_data"))
    print(
        f"Scanned {len(results)} modules, {total_files} files, {_humanize_bytes(total_size)}"
    )
    if ext_count:
        print(f"  {ext_count} module(s) include external (/mnt/ace) data")
    if written:
        print(f"Wrote {len(written)} metadata files:")
        for fp in written:
            print(f"  {fp}")
    elif dry_run:
        print("(dry-run -- no files written)")

    return results


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description="Generate per-module _metadata.json freshness files"
    )
    ap.add_argument("--module", help="Process only this module")
    ap.add_argument("--dry-run", action="store_true", help="Scan without writing")
    ap.add_argument("--project-root", default=None, help="Override project root")
    ap.add_argument(
        "--external-data-root",
        default=None,
        help="Path to external data directory (e.g. /mnt/ace/worldenergydata/data). "
        "Also reads WED_DATA_ROOT env var. Auto-detects /mnt/ace if present.",
    )
    ap.add_argument(
        "--follow-symlinks",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Follow symlinks when scanning (default: True)",
    )
    args = ap.parse_args()

    root = (
        Path(args.project_root)
        if args.project_root
        else Path(__file__).resolve().parent.parent
    )
    ext_root = _resolve_external_root(args.external_data_root)
    if ext_root:
        print(f"External data root: {ext_root}")

    generate_all_metadata(
        root,
        module_filter=args.module,
        external_data_root=ext_root,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
