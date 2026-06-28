# ABOUTME: One-off ingestion: SubseaIQ og_host → curated host registry CSV.
# ABOUTME: Issue #567 calibration v2 — field-linked host facts feed enrichment.
"""Ingest the SubseaIQ ``og_host`` table into a curated, field-linked registry.

The SubseaIQ ``og_host`` table (245 host facilities, ``data`` column = a JSON
blob of ``"Key : Value"`` strings) carries — for its **detailed** Gulf-of-Mexico
records (Spar/TLP/SemiSub hosts) — the one thing the in-repo
``host_facilities.csv`` lacks: a **field link** (``Block(s)``, host reserves,
well counts, and the names of the *subsea-tieback satellite fields* the host
produces). The 147 FPSO records are vessel-spec-only (no block/field link) and
are already represented by ``host_facilities.csv``, so they are skipped here.

This script is a **one-off**: it reads the source table from ``llm-wiki`` (the
SubseaIQ data is stale ~2014 and freely usable — see ``og-website-db/README.md``)
and writes a small committed CSV. The runtime enrichment module
(:mod:`worldenergydata.field_development.host_enrichment`) reads only the
committed CSV — it never depends on ``llm-wiki`` being present.

Run::

    python scripts/field_development/ingest_subseaiq_hosts.py \
        --src /mnt/local-analysis/llm-wiki/data/og-website-db/og_host.csv \
        --out data/modules/offshore_assets/curated/subseaiq_hosts.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional

# The script lives in scripts/field_development/; src is two parents up + src.
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from worldenergydata.field_development.enums import ConceptType  # noqa: E402
from worldenergydata.field_development.subseaiq import (  # noqa: E402
    bsee_block_key,
    key_to_code,
)

# og_host ``type`` column → playbook concept. FPSO is intentionally absent: those
# records are vessel-only (no field link) and already in host_facilities.csv.
HOST_TYPE_CONCEPT: dict[str, ConceptType] = {
    "Spar": ConceptType.SPAR,
    "TLP": ConceptType.TLP,
    "SemiSub": ConceptType.SEMISUB_FPS,
}

OUT_COLUMNS = [
    "host_name",
    "host_concept",
    "general_location",
    "block_raw",
    "bsee_block_key",
    "water_depth_m",
    "reserves_mmboe",
    "total_wells",
    "dry_tree_wells",
    "wet_tree_wells",
    "throughput_mboed",
    "tieback_fields",
]


def _num(text: Optional[str]) -> Optional[float]:
    """First numeric token in a messy value ("~ 75 MBOE" → 75.0, "TBD" → None)."""
    if not text:
        return None
    m = re.search(r"-?\d[\d,]*\.?\d*", str(text))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _flatten(data_cell: str) -> list[tuple[str, str]]:
    """Parse the JSON ``data`` blob to an ordered list of ``(key, value)`` pairs.

    The blob is ``{"<anything>": ["Key : Value", "Section :", ...]}``. Order is
    preserved (the subsea-tieback satellites are a repeated key we must scan in
    order, not collapse into a dict).
    """
    obj = json.loads(data_cell)
    items = obj[next(iter(obj))]
    out: list[tuple[str, str]] = []
    for it in items:
        if " : " not in it:
            out.append((it.strip().rstrip(":").strip(), ""))
            continue
        k, v = it.split(" : ", 1)
        out.append((k.strip(), v.strip()))
    return out


def _parse_tiebacks(pairs: list[tuple[str, str]]) -> list[str]:
    """Collect subsea-tieback satellite field entries ("Swordfish (3)").

    Only the entries under the ``Subsea Tieback Fields`` section count — the same
    ``Field Name & (Wells)`` key is reused elsewhere, so we gate on the section
    header and stop at the next ALL-CAPS section.
    """
    out: list[str] = []
    in_section = False
    for k, v in pairs:
        if k.startswith("Subsea Tieback Fields"):
            in_section = True
            continue
        if not in_section:
            continue
        # A new top-level section (ALL CAPS header) ends the tieback block.
        if v == "" and k.isupper() and len(k) > 3:
            break
        if k.startswith("Field Name") and v:
            # One value can pack several satellites, comma-separated
            # ("Great White (30), Tobago (1)"). Split to one satellite each;
            # a "(n)" well-count never contains a comma, so this is safe.
            for sat in v.split(","):
                sat = sat.strip()
                if sat:
                    out.append(sat)
    return out


def parse_host_row(type_: str, name: str, data_cell: str) -> Optional[dict]:
    """Normalize one detailed og_host record to a registry row, or None to skip.

    Returns None for non-detailed records (FPSO vessel specs, or any row lacking
    a ``Block(s)`` field link).
    """
    concept = HOST_TYPE_CONCEPT.get(type_)
    if concept is None:
        return None
    pairs = _flatten(data_cell)
    d = {k: v for k, v in pairs if v}  # last-wins flat view for scalars
    block_raw = d.get("Block(s)")
    if not block_raw:  # no field link → not a detailed record
        return None
    key = bsee_block_key(block_raw)
    tiebacks = _parse_tiebacks(pairs)
    return {
        "host_name": name.strip(),
        "host_concept": concept.value,
        "general_location": d.get("General Location", ""),
        "block_raw": block_raw,
        "bsee_block_key": key_to_code(key) if key else "",
        "water_depth_m": _num(d.get("Water Depth (m)")),
        "reserves_mmboe": _num(d.get("Reserves (MBOE)")),
        "total_wells": _num(d.get("Total Number of Wells")),
        "dry_tree_wells": _num(d.get("Number of Dry Tree Wells")),
        "wet_tree_wells": _num(d.get("Number of Wet Trees (SS Tiebacks)")),
        "throughput_mboed": _num(
            d.get("Total Throughput Capacity (MBOED)")
            or d.get("TOTAL THROUGHPUT (MBOED)")
        ),
        "tieback_fields": "; ".join(tiebacks),
    }


def ingest(src: Path) -> list[dict]:
    """Parse all detailed host records from an og_host.csv export."""
    csv.field_size_limit(sys.maxsize)
    rows: list[dict] = []
    with open(src, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                parsed = parse_host_row(r["type"], r["name"], r["data"])
            except (json.JSONDecodeError, KeyError):
                continue
            if parsed:
                rows.append(parsed)
    rows.sort(key=lambda x: x["host_name"])
    return rows


def write_csv(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r[c]) for c in OUT_COLUMNS})


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--src",
        type=Path,
        default=Path("/mnt/local-analysis/llm-wiki/data/og-website-db/og_host.csv"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_REPO / "data/modules/offshore_assets/curated/subseaiq_hosts.csv",
    )
    args = ap.parse_args(argv)
    rows = ingest(args.src)
    write_csv(rows, args.out)
    n_tb = sum(1 for r in rows if r["tieback_fields"])
    print(f"wrote {len(rows)} host records ({n_tb} with tiebacks) → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
