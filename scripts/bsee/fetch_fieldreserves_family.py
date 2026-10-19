#!/usr/bin/env python3
"""Fetch annual BOEM archives to a caller-required cache and curate supported members.

Run with --cached to verify and curate a previous fetch without network access.
Monthly Access decoding remains unimplemented and is reported as fetch-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable

import pandas as pd

from worldenergydata.bsee.fieldreserves_fetch import BASE, FILES, fetch_family
from worldenergydata.bsee.fieldreserves_loader import (
    load_appendix,
    load_history,
    load_master,
)


def _cached_frame(
    root: Path, metadata: dict, name: str, reader: Callable[..., pd.DataFrame]
) -> pd.DataFrame:
    body = (root / name).read_bytes()
    expected_url = BASE + "/FieldReserves/Files/" + name.replace(" ", "%20")
    records = [r for r in metadata["records"] if r["source_url"] == expected_url]
    if len(records) != 1:
        raise ValueError(f"Missing or duplicate provenance: {name}")
    record = records[0]
    if (
        hashlib.sha256(body).hexdigest() != record["sha256"]
        or len(body) != record["size_bytes"]
    ):
        raise ValueError(f"Cached source digest/size mismatch: {name}")
    return reader(body, retrieved_utc=record["retrieved_utc"])


def curate_cache(root: Path) -> dict:
    metadata = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name in (
        "curated_history.csv",
        "curated_production_master.csv",
        "curated_appendix.csv",
        "schema.json",
    ):
        target = root / name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Preserving existing output: {name}")
    frames = {
        "history": _cached_frame(root, metadata, FILES[1], load_history),
        "production_master": _cached_frame(root, metadata, FILES[2], load_master),
        "appendix": _cached_frame(root, metadata, FILES[3], load_appendix),
    }
    counts, schema = {}, {}
    for kind, df in frames.items():
        target = root / f"curated_{kind}.csv"
        df.to_csv(target, index=False)
        counts[kind] = len(df)
        schema[kind] = {c: str(d) for c, d in df.dtypes.items()}
    schema["monthly"] = {"status": "fetch_only", "reason": "Access decoder unavailable"}
    schema["units"] = {
        "history": (
            "Oil/gas units not stated in workbook headers; "
            "source values retained without conversion"
        ),
        "production_master": "Oil/condensate: STB; gas: MCF; water unit not stated by source",
        "appendix": "Identifiers only; no physical quantities",
    }
    (root / "schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    if not args.cached:
        fetch_family(args.cache_root)
    counts = curate_cache(args.cache_root)
    print(json.dumps({"rows": counts, "monthly_status": "fetch_only"}, sort_keys=True))


if __name__ == "__main__":
    main()
