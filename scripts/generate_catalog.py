"""Generate per-module schema.yaml files and a top-level data/catalog.yaml.

Scans ``data/modules/`` for CSV, Parquet, and JSON data files, infers column
schemas (name, type, unit), and writes per-module and aggregated catalogs.

Usage:
    python scripts/generate_catalog.py
    python scripts/generate_catalog.py --module bsee
    python scripts/generate_catalog.py --dry-run
"""
from __future__ import annotations

import argparse, csv, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_DATE_RE = [re.compile(p) for p in [
    r"^\d{1,2}/\d{1,2}/\d{4}$", r"^\d{4}-\d{2}-\d{2}", r"^\d{1,2}-[A-Za-z]{3}-\d{4}$"
]]
_UNIT_HINTS = {
    "depth": "feet", "md": "feet", "tvd": "feet",
    "latitude": "degrees", "longitude": "degrees", "lat": "degrees",
    "lon": "degrees", "lng": "degrees",
    "capacity": "tonnes", "mtpa": "MTPA", "weight": "kg", "mbl": "kN",
    "size_mm": "mm", "loa_m": "m", "beam_m": "m", "draft_m": "m",
    "reach_m": "m", "tension_t": "tonnes", "capacity_t": "tonnes",
    "tonnage": "tonnes", "displacement": "tonnes", "area_m2": "m2",
    "speed_knots": "knots", "water_depth": "feet", "water_depth_m": "m",
    "capex_usd": "USD", "storage_m3": "m3",
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
_SKIP_DIRS = {".local", ".claude-flow", "__pycache__", "checkpoints", "cache"}
_SKIP_FILES = {"_metadata.json"}


def _infer_type(values: list[str]) -> str:
    if not values:
        return "string"
    if {v.lower() for v in values} <= {"true", "false", "yes", "no", "1", "0", "t", "f"}:
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


def scan_csv(path: Path, root: Path) -> dict[str, Any]:
    hdr, rows = _sample_csv(path)
    cols = []
    for i, name in enumerate(hdr):
        vals = [r[i] for r in rows if i < len(r) and r[i].strip()]
        cols.append(_col_schema(name, _infer_type(vals)))
    return {"name": path.name, "path": str(path.relative_to(root)), "format": "csv",
            "columns": cols, "row_count": _count_rows(path),
            "size_bytes": path.stat().st_size, "last_modified": _mtime_iso(path)}


def scan_parquet(path: Path, root: Path) -> dict[str, Any]:
    cols, row_count = [], None
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        row_count = len(df)
        for c in df.columns:
            d = str(df[c].dtype)
            t = ("integer" if "int" in d else "float" if "float" in d
                 else "datetime" if "datetime" in d else "boolean" if "bool" in d
                 else "string")
            cols.append(_col_schema(c, t))
    except Exception:
        pass
    return {"name": path.name, "path": str(path.relative_to(root)), "format": "parquet",
            "columns": cols, "row_count": row_count,
            "size_bytes": path.stat().st_size, "last_modified": _mtime_iso(path)}


def scan_json(path: Path, root: Path) -> dict[str, Any]:
    cols = []
    try:
        with open(path, "r", errors="replace") as f:
            data = json.load(f)
        items = data.items() if isinstance(data, dict) else (
            data[0].items() if isinstance(data, list) and data and isinstance(data[0], dict)
            else [])
        cols = [{"name": k, "type": type(v).__name__, "description": "", "unit": ""}
                for k, v in items]
    except Exception:
        pass
    return {"name": path.name, "path": str(path.relative_to(root)), "format": "json",
            "columns": cols, "size_bytes": path.stat().st_size,
            "last_modified": _mtime_iso(path)}


def scan_module(mod_path: Path, root: Path) -> dict[str, Any]:
    datasets: list[dict] = []
    for fp in sorted(mod_path.rglob("*")):
        if not fp.is_file() or fp.name in _SKIP_FILES:
            continue
        parts = fp.relative_to(mod_path).parts
        if any(p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        s = fp.suffix.lower()
        if s == ".csv":
            datasets.append(scan_csv(fp, root))
        elif s == ".parquet":
            datasets.append(scan_parquet(fp, root))
        elif s == ".json" and fp.stat().st_size < 50_000_000:
            lo = fp.name.lower()
            if "metrics" not in lo and "agent" not in lo:
                datasets.append(scan_json(fp, root))
    desc = _MODULE_DESC.get(mod_path.name, f"{mod_path.name} data module")
    if not datasets:
        desc += " (no data files present \u2014 run 'make data' to populate)"
    return {"module": mod_path.name, "description": desc, "datasets": datasets}


def generate_catalog(root: Path, module_filter: str | None = None,
                     dry_run: bool = False) -> dict[str, Any]:
    data_root = root / "data" / "modules"
    if not data_root.exists():
        print(f"Data root not found: {data_root}", file=sys.stderr)
        return {"modules": {}}
    mods: dict[str, Any] = {}
    written: list[str] = []
    for mp in sorted(data_root.iterdir()):
        if not mp.is_dir() or mp.name.startswith("."):
            continue
        if module_filter and mp.name != module_filter:
            continue
        schema = scan_module(mp, root)
        mods[mp.name] = schema
        if not dry_run:
            sp = mp / "schema.yaml"
            with open(sp, "w") as f:
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
            written.append(str(sp.relative_to(root)))
    tot_ds = sum(len(m.get("datasets", [])) for m in mods.values())
    tot_sz = sum(sum(d.get("size_bytes", 0) for d in m.get("datasets", []))
                 for m in mods.values())
    catalog = {"version": "2.0.0", "generated_at": datetime.now(timezone.utc).isoformat(),
               "total_modules": len(mods), "total_datasets": tot_ds,
               "total_size_bytes": tot_sz, "modules": mods}
    if not dry_run:
        cp = root / "data" / "catalog.yaml"
        cp.parent.mkdir(parents=True, exist_ok=True)
        with open(cp, "w") as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=False)
        written.append(str(cp.relative_to(root)))
    print(f"Scanned {len(mods)} modules, {tot_ds} datasets")
    if written:
        print(f"Wrote {len(written)} files:")
        for fp in written:
            print(f"  {fp}")
    elif dry_run:
        print("(dry-run \u2014 no files written)")
    return catalog


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate per-module schema.yaml and aggregated data/catalog.yaml")
    ap.add_argument("--module", help="Process only this module")
    ap.add_argument("--dry-run", action="store_true", help="Scan without writing")
    ap.add_argument("--project-root", default=None, help="Override project root")
    args = ap.parse_args()
    root = Path(args.project_root) if args.project_root else Path(__file__).resolve().parent.parent
    generate_catalog(root, module_filter=args.module, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
