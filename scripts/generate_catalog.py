"""Generate per-module schema.yaml files and a top-level data/catalog.yaml.

Scans ``data/modules/`` for CSV, Parquet, JSON, binary, and zip data files,
infers column schemas (name, type, unit), and writes per-module and
aggregated catalogs.

Supports external data roots (e.g. ``/mnt/ace/worldenergydata/data/``)
via ``--external-data-root`` or the ``WED_DATA_ROOT`` env var.

Usage:
    python scripts/generate_catalog.py
    python scripts/generate_catalog.py --module bsee
    python scripts/generate_catalog.py --dry-run
    python scripts/generate_catalog.py --external-data-root /mnt/ace/worldenergydata/data
"""

from __future__ import annotations

import argparse, csv, json, os, re, sys, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_DATE_RE = [
    re.compile(p)
    for p in [
        r"^\d{1,2}/\d{1,2}/\d{4}$",
        r"^\d{4}-\d{2}-\d{2}",
        r"^\d{1,2}-[A-Za-z]{3}-\d{4}$",
    ]
]
_UNIT_HINTS = {
    "depth": "feet",
    "md": "feet",
    "tvd": "feet",
    "latitude": "degrees",
    "longitude": "degrees",
    "lat": "degrees",
    "lon": "degrees",
    "lng": "degrees",
    "capacity": "tonnes",
    "mtpa": "MTPA",
    "weight": "kg",
    "mbl": "kN",
    "size_mm": "mm",
    "loa_m": "m",
    "beam_m": "m",
    "draft_m": "m",
    "reach_m": "m",
    "tension_t": "tonnes",
    "capacity_t": "tonnes",
    "tonnage": "tonnes",
    "displacement": "tonnes",
    "area_m2": "m2",
    "speed_knots": "knots",
    "water_depth": "feet",
    "water_depth_m": "m",
    "capex_usd": "USD",
    "storage_m3": "m3",
}
_MODULE_DESC = {
    "bsee": "Bureau of Safety and Environmental Enforcement - GOM data",
    "fdas": "Field Development Analysis System - enhanced well data",
    "hse": "Health, Safety and Environment incident data",
    "lng_terminals": "Global LNG terminal infrastructure data",
    "marine_safety": "Maritime casualty and safety incident data",
    "metocean": "Meteorological and oceanographic data",
    "oil_price": "Historical oil price data",
    "pipeline": "Pipeline engineering reference data",
    "pipeline_safety": "PHMSA pipeline safety incident data",
    "subsea": "Subsea equipment and mooring component data",
    "vessel_fleet": "Offshore vessel fleet specifications",
    "vessel_hull_models": "3D vessel hull geometry models",
    "wind": "Wind energy resource and turbine data",
}
_SKIP_DIRS = {
    ".local",
    ".claude-flow",
    "__pycache__",
    "checkpoints",
    "cache",
    ".temp_downloads",
}
_SKIP_FILES = {"_metadata.json"}


def _humanize_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def _load_osha_data_dictionary(dict_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    """Load OSHA data dictionary CSV -> {table: {col: {definition, display_name, datatype}}}."""
    result: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    if not dict_path.exists():
        return result
    try:
        with open(dict_path, "r", newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                table = row.get("table_name", "").strip().strip('"')
                col = row.get("column_name", "").strip().strip('"')
                if table and col:
                    result[table][col] = {
                        "definition": row.get("definition", "").strip().strip('"'),
                        "display_name": row.get("display_name", "").strip().strip('"'),
                        "datatype": row.get("column_datatype", "").strip().strip('"'),
                    }
    except Exception:
        pass
    return result


def scan_binary_directory(dir_path: Path, root: Path) -> dict[str, Any]:
    """Catalog a directory of binary files by extension, count, and total size."""
    ext_counts: dict[str, int] = defaultdict(int)
    ext_sizes: dict[str, int] = defaultdict(int)
    total_files = total_size = 0
    for fp in dir_path.rglob("*"):
        if not fp.is_file():
            continue
        parts = fp.relative_to(dir_path).parts
        if any(p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        ext = fp.suffix.lower() or "(no ext)"
        ext_counts[ext] += 1
        ext_sizes[ext] += fp.stat().st_size
        total_files += 1
        total_size += fp.stat().st_size

    ext_summary = "; ".join(
        f"{ext}: {c} files ({_humanize_bytes(ext_sizes[ext])})"
        for ext, c in sorted(ext_counts.items(), key=lambda x: -x[1])
    )
    try:
        rel = str(dir_path.relative_to(root))
    except ValueError:
        rel = str(dir_path)
    return {
        "name": dir_path.name,
        "path": rel,
        "format": "binary_directory",
        "file_count": total_files,
        "size_bytes": total_size,
        "description": f"Binary data directory: {total_files} files, {_humanize_bytes(total_size)}. {ext_summary}",
        "last_modified": datetime.fromtimestamp(
            dir_path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
    }


def scan_zip(path: Path, root: Path) -> dict[str, Any]:
    """Catalog a zip archive with name, size, and contents listing."""
    contents: list[str] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            contents = zf.namelist()
    except Exception:
        pass
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        rel = str(path)
    return {
        "name": path.name,
        "path": rel,
        "format": "zip",
        "size_bytes": path.stat().st_size,
        "contents": contents[:20],
        "contents_count": len(contents),
        "last_modified": datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
    }


def _infer_type(values: list[str]) -> str:
    if not values:
        return "string"
    if {v.lower() for v in values} <= {
        "true",
        "false",
        "yes",
        "no",
        "1",
        "0",
        "t",
        "f",
    }:
        return "boolean"
    ints = floats = dates = 0
    for v in values:
        v = v.strip()
        if not v:
            continue
        try:
            f = float(v)
            if f == int(f) and "." not in v:
                ints += 1
            else:
                floats += 1
            continue
        except (ValueError, OverflowError):
            pass
        if any(p.match(v) for p in _DATE_RE):
            dates += 1
    n = len(values)
    if dates > n * 0.5:
        return "datetime"
    if (ints + floats) > n * 0.5:
        return "float" if floats else "integer"
    return "string"


def _infer_unit(col: str) -> str:
    low = col.lower()
    for hint, unit in _UNIT_HINTS.items():
        if hint in low:
            return unit
    return ""


def _col_schema(name: str, typ: str) -> dict:
    return {"name": name, "type": typ, "description": "", "unit": _infer_unit(name)}


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _sample_csv(path: Path, n: int = 20) -> tuple[list[str], list[list[str]]]:
    hdr, rows = [], []
    try:
        with open(path, "r", newline="", errors="replace") as f:
            r = csv.reader(f)
            raw = next(r, None)
            if raw:
                hdr = [c.strip() for c in raw]
            for i, row in enumerate(r):
                if i >= n:
                    break
                rows.append(row)
    except Exception:
        pass
    return hdr, rows


def _count_rows(path: Path) -> int | None:
    try:
        with open(path, "r", newline="", errors="replace") as f:
            r = csv.reader(f)
            next(r, None)
            return sum(1 for _ in r)
    except Exception:
        return None


def _rel_path(path: Path, root: Path) -> str:
    """Return relative path if inside root, else absolute."""
    try:
        if path.is_relative_to(root):
            return str(path.relative_to(root))
    except (ValueError, TypeError):
        pass
    return str(path)


def scan_csv(path: Path, root: Path) -> dict[str, Any]:
    hdr, rows = _sample_csv(path)
    cols = []
    for i, name in enumerate(hdr):
        vals = [r[i] for r in rows if i < len(r) and r[i].strip()]
        cols.append(_col_schema(name, _infer_type(vals)))
    return {
        "name": path.name,
        "path": _rel_path(path, root),
        "format": "csv",
        "columns": cols,
        "row_count": _count_rows(path),
        "size_bytes": path.stat().st_size,
        "last_modified": _mtime_iso(path),
    }


def scan_parquet(path: Path, root: Path) -> dict[str, Any]:
    cols, row_count = [], None
    try:
        import pandas as pd

        df = pd.read_parquet(path)
        row_count = len(df)
        for c in df.columns:
            d = str(df[c].dtype)
            t = (
                "integer"
                if "int" in d
                else (
                    "float"
                    if "float" in d
                    else (
                        "datetime"
                        if "datetime" in d
                        else "boolean" if "bool" in d else "string"
                    )
                )
            )
            cols.append(_col_schema(c, t))
    except Exception:
        pass
    return {
        "name": path.name,
        "path": _rel_path(path, root),
        "format": "parquet",
        "columns": cols,
        "row_count": row_count,
        "size_bytes": path.stat().st_size,
        "last_modified": _mtime_iso(path),
    }


def scan_json(path: Path, root: Path) -> dict[str, Any]:
    cols = []
    try:
        with open(path, "r", errors="replace") as f:
            data = json.load(f)
        items = (
            data.items()
            if isinstance(data, dict)
            else (
                data[0].items()
                if isinstance(data, list) and data and isinstance(data[0], dict)
                else []
            )
        )
        cols = [
            {"name": k, "type": type(v).__name__, "description": "", "unit": ""}
            for k, v in items
        ]
    except Exception:
        pass
    return {
        "name": path.name,
        "path": _rel_path(path, root),
        "format": "json",
        "columns": cols,
        "size_bytes": path.stat().st_size,
        "last_modified": _mtime_iso(path),
    }


def _scan_tree(
    mod_path: Path, root: Path, osha_dict: dict | None = None
) -> tuple[list[dict], list[dict]]:
    """Scan a module directory tree, returning (datasets, binary_stores)."""
    datasets: list[dict] = []
    binary_stores: list[dict] = []
    bin_dir = mod_path / "bin"
    zip_dir = mod_path / "zip"

    # Handle bin/ directory as bulk binary stores
    if bin_dir.is_dir():
        for sub in sorted(bin_dir.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                binary_stores.append(scan_binary_directory(sub, root))
        for fp in sorted(bin_dir.iterdir()):
            if fp.is_file() and fp.suffix.lower() == ".bin":
                try:
                    rel = str(fp.relative_to(root))
                except ValueError:
                    rel = str(fp)
                binary_stores.append(
                    {
                        "name": fp.name,
                        "path": rel,
                        "format": "binary",
                        "size_bytes": fp.stat().st_size,
                        "last_modified": datetime.fromtimestamp(
                            fp.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )

    # Handle zip/ directory
    if zip_dir.is_dir():
        for fp in sorted(zip_dir.rglob("*")):
            if fp.is_file() and fp.suffix.lower() == ".zip":
                binary_stores.append(scan_zip(fp, root))

    # Walk remaining files
    for fp in sorted(mod_path.rglob("*")):
        if not fp.is_file() or fp.name in _SKIP_FILES:
            continue
        try:
            parts = fp.relative_to(mod_path).parts
        except ValueError:
            continue
        if parts and parts[0] in ("bin", "zip"):
            continue
        if any(p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        s = fp.suffix.lower()
        if s == ".csv":
            entry = scan_csv(fp, root)
            # Enrich OSHA CSVs with data dictionary
            if osha_dict and "osha" in fp.name.lower():
                table_name = fp.stem
                base_table = re.sub(r"\d+$", "", table_name)
                col_info = osha_dict.get(table_name) or osha_dict.get(base_table) or {}
                if col_info and entry.get("columns"):
                    for col in entry["columns"]:
                        info = col_info.get(col["name"], {})
                        if info.get("definition"):
                            col["description"] = info["definition"]
                        if info.get("datatype"):
                            col["type"] = info["datatype"]
            datasets.append(entry)
        elif s == ".parquet":
            datasets.append(scan_parquet(fp, root))
        elif s == ".json" and fp.stat().st_size < 50_000_000:
            lo = fp.name.lower()
            if "metrics" not in lo and "agent" not in lo:
                datasets.append(scan_json(fp, root))
        elif s == ".zip":
            binary_stores.append(scan_zip(fp, root))

    return datasets, binary_stores


def scan_module(
    mod_path: Path,
    root: Path,
    external_mod_path: Path | None = None,
    osha_dict: dict | None = None,
) -> dict[str, Any]:
    datasets, binary_stores = _scan_tree(mod_path, root, osha_dict=osha_dict)

    # Merge external data if available
    if (
        external_mod_path
        and external_mod_path.is_dir()
        and external_mod_path.resolve() != mod_path.resolve()
    ):
        seen = {d.get("path") for d in datasets} | {
            b.get("path") for b in binary_stores
        }
        ext_ds, ext_bs = _scan_tree(external_mod_path, root, osha_dict=osha_dict)
        for d in ext_ds:
            if d.get("path") not in seen:
                datasets.append(d)
        for b in ext_bs:
            if b.get("path") not in seen:
                binary_stores.append(b)

    desc = _MODULE_DESC.get(mod_path.name, f"{mod_path.name} data module")
    all_entries = datasets + binary_stores
    if not all_entries:
        desc += " (no data files present \u2014 run 'make data' to populate)"
    total_size = sum(e.get("size_bytes", 0) for e in all_entries)
    if total_size > 0:
        desc += f" [{_humanize_bytes(total_size)}]"
    return {
        "module": mod_path.name,
        "description": desc,
        "datasets": datasets,
        "binary_stores": binary_stores,
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


def generate_catalog(
    root: Path,
    module_filter: str | None = None,
    dry_run: bool = False,
    external_data_root: Path | None = None,
) -> dict[str, Any]:
    data_root = root / "data" / "modules"
    ext_modules = external_data_root / "modules" if external_data_root else None

    if not data_root.exists() and not ext_modules:
        print(f"Data root not found: {data_root}", file=sys.stderr)
        return {"modules": {}}

    # Collect all module names from both roots
    module_names: set[str] = set()
    if data_root.exists():
        for mp in data_root.iterdir():
            if mp.is_dir() and not mp.name.startswith("."):
                module_names.add(mp.name)
    if ext_modules and ext_modules.is_dir():
        for mp in ext_modules.iterdir():
            if mp.is_dir() and not mp.name.startswith("."):
                module_names.add(mp.name)

    # Load OSHA data dictionary if available
    osha_dict = None
    candidates = [data_root / "hse" / "raw" / "osha" / "osha_data_dictionary.csv"]
    if ext_modules:
        candidates.insert(
            0, ext_modules / "hse" / "raw" / "osha" / "osha_data_dictionary.csv"
        )
    for cand in candidates:
        if cand.exists():
            osha_dict = _load_osha_data_dictionary(cand)
            break

    mods: dict[str, Any] = {}
    written: list[str] = []
    for name in sorted(module_names):
        if module_filter and name != module_filter:
            continue
        mp = data_root / name
        ext_mp = ext_modules / name if ext_modules else None
        if not mp.exists() and ext_mp and ext_mp.is_dir():
            mp = ext_mp
            ext_mp = None

        use_osha = osha_dict if name == "hse" else None
        schema = scan_module(mp, root, external_mod_path=ext_mp, osha_dict=use_osha)
        mods[name] = schema
        if not dry_run and mp.is_relative_to(root):
            sp = mp / "schema.yaml"
            with open(sp, "w") as f:
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
            written.append(str(sp.relative_to(root)))

    tot_ds = sum(len(m.get("datasets", [])) for m in mods.values())
    tot_bs = sum(len(m.get("binary_stores", [])) for m in mods.values())
    tot_sz = sum(
        sum(d.get("size_bytes", 0) for d in m.get("datasets", []))
        + sum(b.get("size_bytes", 0) for b in m.get("binary_stores", []))
        for m in mods.values()
    )
    catalog = {
        "version": "2.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_modules": len(mods),
        "total_datasets": tot_ds + tot_bs,
        "total_size_bytes": tot_sz,
        "modules": mods,
    }
    if not dry_run:
        cp = root / "data" / "catalog.yaml"
        cp.parent.mkdir(parents=True, exist_ok=True)
        with open(cp, "w") as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=False)
        written.append(str(cp.relative_to(root)))
    print(f"Scanned {len(mods)} modules, {tot_ds} datasets, {tot_bs} binary stores")
    print(f"Total size: {_humanize_bytes(tot_sz)}")
    if written:
        print(f"Wrote {len(written)} files:")
        for fp in written:
            print(f"  {fp}")
    elif dry_run:
        print("(dry-run \u2014 no files written)")
    return catalog


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate per-module schema.yaml and aggregated data/catalog.yaml"
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
    generate_catalog(
        root,
        module_filter=args.module,
        dry_run=args.dry_run,
        external_data_root=ext_root,
    )


if __name__ == "__main__":
    main()
